# gemini/resources/core/story_manager.py

import json
import os
import time
import hashlib
from datetime import datetime
from filesystem import fs_manager

class StoryManager:
    def _get_story_path(self, current_path):
        """Finds the .story directory starting from current_path and going up."""
        path = fs_manager.get_absolute_path(current_path)
        while path != '/':
            story_dir = os.path.join(path, '.story')
            if fs_manager.get_node(story_dir):
                return story_dir
            path = os.path.dirname(path)
        # Check root last
        story_dir = os.path.join('/', '.story')
        if fs_manager.get_node(story_dir):
            return story_dir
        return None

    def init(self, current_path, user_context):
        """Initializes a new story repository in the current directory."""
        story_path = os.path.join(fs_manager.get_absolute_path(current_path), '.story')
        if fs_manager.get_node(story_path):
            return {"success": False, "error": "A story has already begun in this directory."}

        try:
            fs_manager.create_directory(story_path, user_context)
            fs_manager.create_directory(os.path.join(story_path, 'snapshots'), user_context)
            fs_manager.write_file(os.path.join(story_path, 'log.json'), '[]', user_context)
            fs_manager.chmod(story_path, "770")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": f"Failed to initialize story: {repr(e)}"}

    def _get_tracked_files(self, work_dir):
        """Recursively finds all non-hidden files to be tracked."""
        tracked = []

        def recurse(current_path):
            node = fs_manager.get_node(current_path)
            if not node:
                return

            if node.get('type') == 'directory':
                # Skip the .story directory itself
                if os.path.basename(current_path) == '.story':
                    return
                for child_name, child_node in node.get('children', {}).items():
                    if not child_name.startswith('.'):
                        recurse(os.path.join(current_path, child_name))
            elif node.get('type') == 'file':
                tracked.append(current_path)

        recurse(work_dir)
        return tracked

    def create_snapshot(self, work_dir, user_context):
        """Creates a snapshot of all tracked files."""
        story_path = self._get_story_path(work_dir)
        if not story_path:
            return {"success": False, "error": "Not a story repository. Run 'story begin' first."}

        tracked_files = self._get_tracked_files(work_dir)
        if not tracked_files:
            return {"success": False, "error": "No files to save."}

        timestamp = str(time.time_ns())
        snapshot_id = hashlib.sha1(timestamp.encode()).hexdigest()[:10]
        snapshot_dir = os.path.join(story_path, 'snapshots', snapshot_id)

        try:
            fs_manager.create_directory(snapshot_dir, user_context)
            for file_path in tracked_files:
                relative_path = os.path.relpath(file_path, work_dir)
                dest_path = os.path.join(snapshot_dir, relative_path)

                # Ensure parent directory exists in snapshot
                dest_parent = os.path.dirname(dest_path)
                if not fs_manager.get_node(dest_parent):
                    fs_manager.create_directory(dest_parent, user_context, parents=True)

                source_node = fs_manager.get_node(file_path)
                if source_node:
                    fs_manager.write_file(dest_path, source_node.get('content', ''), user_context)

            return {"success": True, "snapshot_id": snapshot_id}
        except Exception as e:
            return {"success": False, "error": f"Failed to create snapshot: {repr(e)}"}

    def add_log_entry(self, story_path, message, snapshot_id, user_context):
        """Adds a new chapter to the log."""
        log_path = os.path.join(story_path, 'log.json')
        log_node = fs_manager.get_node(log_path)
        if not log_node:
            return {"success": False, "error": "log.json not found."}

        try:
            log_data = json.loads(log_node.get('content', '[]'))
            new_entry = {
                "id": snapshot_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "message": message,
                "author": user_context.get('name'),
                "snapshot": snapshot_id
            }
            log_data.insert(0, new_entry) # Prepend to keep newest first
            fs_manager.write_file(log_path, json.dumps(log_data, indent=2), user_context)
            return {"success": True}
        except (json.JSONDecodeError, Exception) as e:
            return {"success": False, "error": f"Failed to update log: {repr(e)}"}

    def read_log(self, story_path):
        """Reads and returns the log data."""
        log_path = os.path.join(story_path, 'log.json')
        log_node = fs_manager.get_node(log_path)
        if not log_node:
            return {"success": False, "error": "log.json not found."}

        try:
            log_data = json.loads(log_node.get('content', '[]'))
            return {"success": True, "data": log_data}
        except json.JSONDecodeError:
            return {"success": False, "error": "Could not parse log.json."}

    def restore_snapshot(self, work_dir, snapshot_id, user_context):
        """Restores a snapshot to the working directory."""
        story_path = self._get_story_path(work_dir)
        if not story_path:
            return {"success": False, "error": "Not a story repository."}

        snapshot_dir = os.path.join(story_path, 'snapshots', snapshot_id)
        snapshot_node = fs_manager.get_node(snapshot_dir)
        if not snapshot_node:
            return {"success": False, "error": f"Snapshot '{snapshot_id}' not found."}

        try:
            # This is a destructive operation. First, we clear the tracked files.
            tracked_files = self._get_tracked_files(work_dir)
            for file_path in tracked_files:
                fs_manager.remove(file_path)

            # Now, copy files from snapshot to work_dir
            def recurse_copy(current_snapshot_path, current_work_path):
                node = fs_manager.get_node(current_snapshot_path)
                if not node: return

                if node.get('type') == 'directory':
                    if not fs_manager.get_node(current_work_path):
                        fs_manager.create_directory(current_work_path, user_context)
                    for child_name, child_node in node.get('children', {}).items():
                        recurse_copy(os.path.join(current_snapshot_path, child_name), os.path.join(current_work_path, child_name))
                elif node.get('type') == 'file':
                    fs_manager.write_file(current_work_path, node.get('content', ''), user_context)

            recurse_copy(snapshot_dir, work_dir)

            return {"success": True}
        except Exception as e:
            return {"success": False, "error": f"Failed to restore snapshot: {repr(e)}"}

    def get_story_summary(self, story_path):
        """Generates a summary of the story for chidi."""
        log_result = self.read_log(story_path)
        if not log_result["success"]:
            return {"success": False, "error": log_result["error"]}

        log_data = log_result["data"]

        summary = [f"# Story Summary for {os.path.basename(os.path.dirname(story_path))}"]
        summary.append(f"\nThis story contains {len(log_data)} chapters.\n")

        for entry in reversed(log_data):
            summary.append(f"## Chapter: {entry['message']}")
            summary.append(f"- **ID:** {entry['id']}")
            summary.append(f"- **Author:** {entry.get('author', 'unknown')}")
            summary.append(f"- **Date:** {entry['timestamp']}")

        return {"success": True, "data": "\n".join(summary)}

# Instantiate a singleton for the kernel
story_manager = StoryManager()
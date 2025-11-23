// scripts/asset_manifest.js

window.FRACTAL_ASSET_MANIFEST = {
    // CSS files can be loaded in parallel.
    css: [
        "./main.css",
        "./scripts/apps/apps.css",
        "./scripts/apps/editor/editor.css",
        "./scripts/apps/chidi/chidi.css",
        "./scripts/apps/gemini_chat/gemini_chat.css",
        "./scripts/apps/adventure/adventure.css",
        "./scripts/apps/log/log.css",
        "./scripts/apps/paint/paint.css",
        "./scripts/apps/basic/basic.css",
        "./scripts/apps/top/top.css",
        "./scripts/apps/onboarding/onboarding.css"
    ],
    // JavaScript files must be loaded in a specific order to respect dependencies.
    js: [
        // External Libraries
        "./dep/marked.min.js",
        "./dep/purify.min.js",
        "./dep/html2canvas.min.js",
        "./dep/tone.js",
        "./dep/pyodide/pyodide.js",

        // Core Utilities & Managers (Order is critical)
        "./scripts/utils.js",
        "./scripts/ui_components.js",
        "./scripts/ui_state_manager.js",
        "./scripts/config.js",
        "./scripts/ai_manager.js",
        "./scripts/error_handler.js",
        "./scripts/storage.js",
        "./scripts/session_manager.js",
        "./scripts/output_manager.js",
        "./scripts/group_manager.js",
        "./scripts/fs_manager.js",
        "./scripts/user_manager.js",
        "./scripts/sudo_manager.js",
        "./scripts/terminal_ui.js",
        "./scripts/modal_manager.js",
        "./scripts/sound_manager.js",
        "./scripts/message_bus_manager.js",

        // App Base Class & Pager
        "./scripts/apps/app.js",
        "./scripts/pager.js",

        // Application Modules (UI first, then Manager)
        "./scripts/apps/editor/editor_ui.js",
        "./scripts/apps/editor/editor_manager.js",
        "./scripts/apps/adventure/adventure_ui.js",
        "./scripts/apps/adventure/adventure_create.js",
        "./scripts/apps/adventure/adventure_manager.js",
        "./scripts/apps/paint/paint_ui.js",
        "./scripts/apps/paint/paint_manager.js",
        "./scripts/apps/chidi/chidi_ui.js",
        "./scripts/apps/chidi/chidi_manager.js",
        "./scripts/apps/top/top_ui.js",
        "./scripts/apps/top/top_manager.js",
        "./scripts/apps/log/log_ui.js",
        "./scripts/apps/log/log_manager.js",
        "./scripts/apps/basic/basic_ui.js",
        "./scripts/apps/basic/basic_manager.js",
        "./scripts/apps/onboarding/onboarding_ui.js",
        "./scripts/apps/onboarding/onboarding_manager.js",
        "./scripts/apps/gemini_chat/gemini_chat_ui.js",
        "./scripts/apps/gemini_chat/gemini_chat_manager.js",

        // High-level Managers and Core Logic
        "./scripts/theme_manager.js",
        "./scripts/command_registry.js",
        "./scripts/network_manager.js",
        "./scripts/audit_manager.js",
        "./scripts/job_handler.js",
        "./scripts/effect_handler.js",
        "./scripts/boot.js",
        "./main.js",
        "./bridge.js"
    ]
};
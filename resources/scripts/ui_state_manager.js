// scripts/ui_state_manager.js

class UIStateManager {
    constructor() {
        this.isCinematicMode = false;
        this.dependencies = {};
    }

    setDependencies(dependencies) {
        this.dependencies = dependencies;
    }

    toggleCinematicMode(mode = null) {
        const { OutputManager, Config } = this.dependencies;
        if (mode === 'on') {
            this.isCinematicMode = true;
        } else if (mode === 'off') {
            this.isCinematicMode = false;
        } else {
            this.isCinematicMode = !this.isCinematicMode;
        }

        const status = this.isCinematicMode ? "ON" : "OFF";
        // Use _appendDirectly to avoid the cinematic effect on the confirmation message
        OutputManager._appendDirectly(`Cinematic mode is now ${status}.`, {
            typeClass: Config.CSS_CLASSES.INFO_MSG
        });

        return this.isCinematicMode;
    }

    isCinematic() {
        return this.isCinematicMode;
    }
}
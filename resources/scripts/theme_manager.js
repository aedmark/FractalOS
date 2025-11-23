// gemini/scripts/theme_manager.js

class ThemeManager {
    constructor() {
        this.dependencies = {};
        this.currentTheme = {};
    }

    setDependencies(dependencies) {
        this.dependencies = dependencies;
    }

    async loadAndApplyInitialTheme() {
        const defaultTheme = {
            name: "FractalOS Default",
            colors: {},
            fonts: {},
            sounds: {
                beepNote: "G5"
            }
        };
        // We can apply the object directly since we have it here
        await this.applyTheme(defaultTheme);
    }

    async applyTheme(themeOrName) {
        let themeData;
        if (typeof themeOrName === 'string') {
            themeData = await this._fetchThemeData(themeOrName);
            if (!themeData) {
                console.error(`ThemeManager: Could not fetch data for theme '${themeOrName}'.`);
                return;
            }
        } else if (typeof themeOrName === 'object') {
            themeData = themeOrName;
        } else {
            console.error("ThemeManager: applyTheme requires a theme name or object.");
            return;
        }

        this.currentTheme = themeData;
        this._applyColors(themeData.colors);
        this._applyFonts(themeData.fonts);

        if (this.dependencies.SoundManager && themeData.sounds) {
            this.dependencies.SoundManager.loadSoundPack(themeData.sounds);
        }
    }

    _applyColors(colors = {}) {
        const styleId = 'dynamic-theme-styles';
        let styleElement = document.getElementById(styleId);
        if (!styleElement) {
            styleElement = this.dependencies.Utils.createElement('style', { id: styleId });
            document.head.appendChild(styleElement);
        }

        const colorOverrides = Object.entries(colors)
            .map(([key, value]) => `    --${key}: ${value};`)
            .join('\n');

        // Clear previous font rules before adding new color rules
        const existingContent = styleElement.textContent || '';
        const fontRootRegex = /:root\s*\{[^}]*--font-family-[^}]*\}/g;
        const fontRules = existingContent.match(fontRootRegex) || [];

        styleElement.textContent = `:root {\n${colorOverrides}\n}\n${fontRules.join('\n')}`;
    }

    _applyFonts(fonts = {}) {
        const { Utils } = this.dependencies;
        if (fonts.googleFontUrl) {
            const fontId = 'dynamic-theme-font';
            let fontLink = document.getElementById(fontId);
            if (!fontLink) {
                fontLink = Utils.createElement('link', { id: fontId, rel: 'stylesheet' });
                document.head.appendChild(fontLink);
            }
            fontLink.href = fonts.googleFontUrl;
        }

        const styleElement = document.getElementById('dynamic-theme-styles');
        if (styleElement) {
            let fontCss = '';
            if (fonts.mono) {
                fontCss += `    --font-family-mono: ${fonts.mono};\n`;
            }
            if (fonts.sans) {
                fontCss += `    --font-family-sans: ${fonts.sans};\n`;
            }
            if (fontCss) {
                styleElement.textContent += `\n:root {\n${fontCss}}`;
            }
        }
    }

    async _fetchThemeData(themeName) {
        const { CommandExecutor } = this.dependencies;
        // Escape quotes in the theme name for the command
        const escapedThemeName = themeName.replace(/"/g, '\\"');
        const command = `theme get "${escapedThemeName}"`;

        const result = await CommandExecutor.processSingleCommand(command, { isInteractive: false });

        if (result.success) {
            try {
                // The command output is the raw JSON string
                return JSON.parse(result.output);
            } catch (e) {
                console.error(`Failed to parse theme JSON for '${themeName}':`, e);
                return null;
            }
        } else {
            console.error(`Failed to fetch theme data for '${themeName}':`, result.error);
            return null;
        }
    }
}
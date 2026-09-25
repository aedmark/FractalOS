class StorageManager {
    constructor() {
        this.dependencies = {};
    }

    setDependencies(dependencies) {
        this.dependencies = dependencies;
    }

    loadItem(key, itemName, defaultValue = null) {
        try {
            const storedValue = localStorage.getItem(key);
            if (storedValue !== null) {
                try {
                    return JSON.parse(storedValue);
                } catch (e) {
                    return storedValue;
                }
            }
        } catch (e) {
            console.warn(`Could not load ${itemName} from localStorage. Error: ${e.message}`);
        }
        return defaultValue;
    }

    saveItem(key, data, itemName) {
        try {
            const valueToStore =
                typeof data === "object" && data !== null
                    ? JSON.stringify(data)
                    : String(data);
            localStorage.setItem(key, valueToStore);
            return true;
        } catch (e) {
            console.error(`Error saving ${itemName} to localStorage. Error: ${e.message}`);
        }
        return false;
    }

    removeItem(key) {
        try {
            localStorage.removeItem(key);
        } catch (e) {
            console.warn(`Could not remove item for key '${key}'. Error: ${e.message}`);
        }
    }

    exportLocalStorage() {
        const data = {};
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            data[key] = localStorage.getItem(key);
        }
        return JSON.stringify(data, null, 2);
    }

    importLocalStorage(jsonString) {
        try {
            const data = JSON.parse(jsonString);
            localStorage.clear();
            for (const key in data) {
                if (Object.hasOwnProperty.call(data, key)) {
                    localStorage.setItem(key, data[key]);
                }
            }
        } catch (e) {
            console.error("Failed to import localStorage data:", e);
        }
    }
}


class IndexedDBManager {
    constructor() {
        this.dbInstance = null;
        this.dependencies = {};
    }

    setDependencies(dependencies) {
        this.dependencies = dependencies;
    }

    init() {
        const { Config, OutputManager } = this.dependencies;
        return new Promise((resolve, reject) => {
            if (!window.indexedDB) {
                reject(new Error("IndexedDB not supported."));
                return;
            }
            const request = indexedDB.open(Config.DATABASE.NAME, Config.DATABASE.VERSION);
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains(Config.DATABASE.FS_STORE_NAME)) {
                    db.createObjectStore(Config.DATABASE.FS_STORE_NAME, { keyPath: "id" });
                }
            };
            request.onsuccess = (event) => {
                this.dbInstance = event.target.result;
                resolve(this.dbInstance);
            };
            request.onerror = (event) => reject(event.target.error);
        });
    }

    async save(fsData) {
        const { Config } = this.dependencies;
        return new Promise((resolve) => {
            const transaction = this.dbInstance.transaction(Config.DATABASE.FS_STORE_NAME, "readwrite");
            const store = transaction.objectStore(Config.DATABASE.FS_STORE_NAME);
            const request = store.put({ id: Config.DATABASE.UNIFIED_FS_KEY, data: fsData });
            request.onsuccess = () => resolve(true);
            request.onerror = () => resolve(false);
        });
    }

    async load() {
        const { Config } = this.dependencies;
        return new Promise((resolve) => {
            const transaction = this.dbInstance.transaction(Config.DATABASE.FS_STORE_NAME, "readonly");
            const store = transaction.objectStore(Config.DATABASE.FS_STORE_NAME);
            const request = store.get(Config.DATABASE.UNIFIED_FS_KEY);
            request.onsuccess = () => resolve(request.result ? request.result.data : null);
            request.onerror = () => resolve(null);
        });
    }

    async clear() {
        const { Config } = this.dependencies;
        return new Promise((resolve, reject) => {
            if (this.dbInstance) {
                this.dbInstance.close();
                this.dbInstance = null;
            }
            const deleteRequest = indexedDB.deleteDatabase(Config.DATABASE.NAME);
            deleteRequest.onsuccess = () => resolve(true);
            deleteRequest.onerror = (e) => reject(e.target.error);
        });
    }
}

class NeutralinoFSManager {
    constructor() {
        this.fsFilePath = null;
        this.localStorageFilePath = null;
    }

    setDependencies(dependencies) {
    }

    async init() {
        try {
            const dataDir = `${NL_PATH}/data`;
            this.fsFilePath = `${dataDir}/fractalos_fs.json`;
            this.localStorageFilePath = `${dataDir}/fractalos_localstorage.json`;
            try {
                await Neutralino.filesystem.getStats(dataDir);
            } catch (e) {
                await Neutralino.filesystem.createDirectory(dataDir);
            }
            return true;
        } catch (e) {
            alert(`Critical Error: Could not initialize portable storage.\n\n${e.message}`);
            return false;
        }
    }

    async save(fsData) {
        try {
            await Neutralino.filesystem.writeFile(this.fsFilePath, JSON.stringify(fsData, null, 2));
            return true;
        } catch (e) {
            console.error("NeutralinoFS Save Error:", e);
            return false;
        }
    }

    async load() {
        try {
            const jsonString = await Neutralino.filesystem.readFile(this.fsFilePath);
            return JSON.parse(jsonString);
        } catch (e) {
            if (e.code === 'NE_FS_FILENOTF') return null;
            console.error("NeutralinoFS Load Error:", e);
            return null;
        }
    }

    async clear() {
        try {
            await Neutralino.filesystem.removeFile(this.fsFilePath);
            return true;
        } catch (e) {
            if (e.code === 'NE_FS_FILENOTF') return true;
            console.error("NeutralinoFS Clear Error:", e);
            return false;
        }
    }

    async saveLocalStorage(jsonData) {
        try {
            await Neutralino.filesystem.writeFile(this.localStorageFilePath, jsonData);
            return true;
        } catch (e) {
            console.error("NeutralinoFS localStorage Save Error:", e);
            return false;
        }
    }

    async loadLocalStorage() {
        try {
            const stats = await Neutralino.filesystem.getStats(this.localStorageFilePath);
            if (stats.size === 0) {
                return null;
            }
            return await Neutralino.filesystem.readFile(this.localStorageFilePath);
        } catch (e) {
            if (e.code === 'NE_FS_FILENOTF') {
                return null;
            }
            console.error("NeutralinoFS localStorage Load Error:", e);
            return null;
        }
    }
}


class StorageHAL {
    constructor() {
        this.dependencies = {};
        this.backend = null;
    }

    setDependencies(dependencies) {
        this.dependencies = dependencies;
    }

    async init() {
        if (typeof Neutralino !== 'undefined' && window.NL_PORT) {
            console.log("Portable mode detected. Using native file system storage.");
            this.backend = new NeutralinoFSManager();
        } else {
            console.log("Browser mode detected. Using IndexedDB storage.");
            this.backend = new IndexedDBManager();
        }

        this.backend.setDependencies(this.dependencies);
        return this.backend.init();
    }

    async save(fsData) {
        if (!this.backend) throw new Error("StorageHAL not initialized.");
        return this.backend.save(fsData);
    }

    async load() {
        if (!this.backend) throw new Error("StorageHAL not initialized.");
        return this.backend.load();
    }

    async clear() {
        if (!this.backend) throw new Error("StorageHAL not initialized.");
        return this.backend.clear();
    }

    async saveLocalStorage(jsonData) {
        if (this.backend && typeof this.backend.saveLocalStorage === 'function') {
            return this.backend.saveLocalStorage(jsonData);
        }
    }

    async loadLocalStorage() {
        if (this.backend && typeof this.backend.loadLocalStorage === 'function') {
            return this.backend.loadLocalStorage();
        }
        return null;
    }
}
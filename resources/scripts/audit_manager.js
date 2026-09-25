class AuditManager {
    constructor() {
        this.dependencies = {};
    }

    setDependencies(dependencies) {
        this.dependencies = dependencies;
    }

    async log(actor, action, details) {
        const { UserManager } = this.dependencies;
        const currentUserContext = { name: (await UserManager.getCurrentUser()).name };
        const resultJson = await FractalOS_Kernel.syscall("audit", "log", [actor, action, details, currentUserContext]);
        const result = JSON.parse(resultJson);
        if (!result.success) {
            console.error("AuditManager syscall failed:", result.error);
        }
    }
}
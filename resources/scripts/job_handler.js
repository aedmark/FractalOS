// --- Job Management Globals ---
let backgroundProcessIdCounter = 0;
const activeJobs = {};

// --- Job Signal Handler ---
function sendSignalToJob(jobId, signal) {
    const job = activeJobs[jobId];
    if (!job) return { success: false, error: `Job ${jobId} not found.` };
    switch (signal.toUpperCase()) {
        case 'KILL': case 'TERM':
            if (job.abortController) {
                job.abortController.abort("Killed by user.");
                delete activeJobs[jobId];
                dependencies.MessageBusManager.unregisterJob(jobId);
            }
            break;
        case 'STOP': job.status = 'paused'; break;
        case 'CONT': job.status = 'running'; break;
        default: return { success: false, error: `Invalid signal '${signal}'.` };
    }
    return { success: true, output: `Signal ${signal} sent to job ${jobId}.` };
}
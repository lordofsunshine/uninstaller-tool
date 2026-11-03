namespace UninstallerTool.Models
{
    public sealed class UninstallResult
    {
        public string ProgramKey { get; set; } = string.Empty;

        public string Name { get; set; } = string.Empty;

        public bool Success { get; set; }

        public int? ExitCode { get; set; }

        public bool RebootRequired { get; set; }

        public bool StillRunning { get; set; }

        public string Message { get; set; } = string.Empty;
    }

    public sealed class UninstallProgress
    {
        public int Done { get; set; }

        public int Total { get; set; }

        public string ProgramKey { get; set; } = string.Empty;

        public ProgramStatus Status { get; set; }

        public string Message { get; set; } = string.Empty;
    }

    public sealed class UninstallSummary
    {
        public System.Collections.Generic.List<UninstallResult> Results { get; } =
            new System.Collections.Generic.List<UninstallResult>();

        public System.Collections.Generic.List<UninstallerTool.Models.ProgramEntry> Uninstalled { get; } =
            new System.Collections.Generic.List<UninstallerTool.Models.ProgramEntry>();

        public System.Collections.Generic.List<string> RebootRequired { get; } = new System.Collections.Generic.List<string>();
    }
}

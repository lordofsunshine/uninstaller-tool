using System.Collections.Generic;

namespace UninstallerTool.Models
{
    public sealed class Leftovers
    {
        public string ProgramKey { get; set; } = string.Empty;

        public string ProgramName { get; set; } = string.Empty;

        public List<string> Files { get; set; } = new List<string>();

        public List<RegistryEntry> Registry { get; set; } = new List<RegistryEntry>();

        public bool TimedOut { get; set; }

        public bool HasItems => Files.Count > 0 || Registry.Count > 0;
    }

    public sealed class RemovalResult
    {
        public int RemovedFiles { get; set; }

        public int RemovedRegistry { get; set; }

        public int ScheduledFiles { get; set; }

        public List<string> Errors { get; } = new List<string>();

        public List<string> Backups { get; } = new List<string>();
    }
}

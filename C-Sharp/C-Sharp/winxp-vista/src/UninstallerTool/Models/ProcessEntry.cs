namespace UninstallerTool.Models
{
    public sealed class ProcessEntry
    {
        public ProcessEntry(int pid, string name, string executable)
        {
            Pid = pid;
            Name = name ?? "?";
            Executable = executable ?? string.Empty;
        }

        public int Pid { get; }

        public string Name { get; }

        public string Executable { get; }
    }
}

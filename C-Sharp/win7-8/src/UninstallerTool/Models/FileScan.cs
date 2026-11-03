using System.Collections.Generic;

namespace UninstallerTool.Models
{
    public readonly struct ScannedFile
    {
        public ScannedFile(string path, long size)
        {
            Path = path;
            Size = size;
        }

        public string Path { get; }

        public long Size { get; }
    }

    public sealed class FileScan
    {
        public List<ScannedFile> Files { get; set; } = new List<ScannedFile>();

        public long TotalCount { get; set; }

        public long TotalSize { get; set; }

        public List<string> Directories { get; } = new List<string>();

        public bool Truncated { get; set; }

        public bool Cancelled { get; set; }
    }
}

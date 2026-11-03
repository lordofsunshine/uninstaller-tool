namespace UninstallerTool.Models
{
    public enum RegistryEntryKind
    {
        Uninstall,
        Vendor
    }

    public sealed class RegistryEntry
    {
        public RegistryEntry(string hive, string subkey, string displayName, string keyName, RegistryEntryKind kind)
        {
            Hive = hive ?? string.Empty;
            Subkey = subkey ?? string.Empty;
            DisplayName = displayName ?? string.Empty;
            KeyName = keyName ?? string.Empty;
            Kind = kind;
        }

        public string Hive { get; }

        public string Subkey { get; }

        public string DisplayName { get; }

        public string KeyName { get; }

        public RegistryEntryKind Kind { get; }

        public string Path => Hive + "\\" + Subkey;

        public override string ToString()
        {
            return Path;
        }
    }
}

using System.Runtime.Serialization;

namespace UninstallerTool.Models
{
    [DataContract]
    public sealed class ProgramDto
    {
        [DataMember(Name = "name")]
        public string Name { get; set; }

        [DataMember(Name = "uninstall_string")]
        public string UninstallString { get; set; }

        [DataMember(Name = "quiet_uninstall_string")]
        public string QuietUninstallString { get; set; }

        [DataMember(Name = "install_location")]
        public string InstallLocation { get; set; }

        [DataMember(Name = "publisher")]
        public string Publisher { get; set; }

        [DataMember(Name = "install_date")]
        public string InstallDate { get; set; }

        [DataMember(Name = "version")]
        public string Version { get; set; }

        [DataMember(Name = "size_kb")]
        public long SizeKb { get; set; }

        [DataMember(Name = "icon")]
        public string Icon { get; set; }

        [DataMember(Name = "source")]
        public string Source { get; set; }

        [DataMember(Name = "package_full_name")]
        public string PackageFullName { get; set; }

        [DataMember(Name = "package_family")]
        public string PackageFamily { get; set; }

        [DataMember(Name = "registry_hive")]
        public string RegistryHive { get; set; }

        [DataMember(Name = "registry_subkey")]
        public string RegistrySubkey { get; set; }

        public static ProgramDto FromProgram(ProgramEntry program)
        {
            return new ProgramDto
            {
                Name = program.Name,
                UninstallString = program.UninstallString,
                QuietUninstallString = program.QuietUninstallString,
                InstallLocation = program.InstallLocation,
                Publisher = program.Publisher,
                InstallDate = program.InstallDate,
                Version = program.Version,
                SizeKb = program.SizeKb,
                Icon = program.Icon,
                Source = program.Source == ProgramSource.Store ? "store" : "registry",
                PackageFullName = program.PackageFullName,
                PackageFamily = program.PackageFamily,
                RegistryHive = program.RegistryHive,
                RegistrySubkey = program.RegistrySubkey
            };
        }

        public ProgramEntry ToProgram()
        {
            return new ProgramEntry
            {
                Name = Name ?? string.Empty,
                UninstallString = UninstallString ?? string.Empty,
                QuietUninstallString = QuietUninstallString ?? string.Empty,
                InstallLocation = InstallLocation ?? string.Empty,
                Publisher = Publisher ?? string.Empty,
                InstallDate = InstallDate ?? string.Empty,
                Version = Version ?? string.Empty,
                SizeKb = SizeKb > 0 ? SizeKb : 0,
                Icon = Icon ?? string.Empty,
                Source = Source == "store" ? ProgramSource.Store : ProgramSource.Registry,
                PackageFullName = PackageFullName ?? string.Empty,
                PackageFamily = PackageFamily ?? string.Empty,
                RegistryHive = RegistryHive ?? string.Empty,
                RegistrySubkey = RegistrySubkey ?? string.Empty
            };
        }
    }

    [DataContract]
    public sealed class StoreCacheDto
    {
        [DataMember(Name = "saved_at")]
        public long SavedAt { get; set; }

        [DataMember(Name = "programs")]
        public ProgramDto[] Programs { get; set; }
    }
}

using System;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using UninstallerTool.Infrastructure;

namespace UninstallerTool.Models
{
    public enum ProgramSource
    {
        Registry,
        Store
    }

    public enum ProgramStatus
    {
        Idle,
        Running,
        Success,
        Error
    }

    public sealed class ProgramEntry : INotifyPropertyChanged
    {
        private bool _checked;
        private ProgramStatus _status;
        private long _sizeKb;

        public string Name { get; set; } = string.Empty;

        public string UninstallString { get; set; } = string.Empty;

        public string QuietUninstallString { get; set; } = string.Empty;

        public string InstallLocation { get; set; } = string.Empty;

        public string Publisher { get; set; } = string.Empty;

        public string InstallDate { get; set; } = string.Empty;

        public string Version { get; set; } = string.Empty;

        public long SizeKb
        {
            get => _sizeKb;
            set
            {
                if (_sizeKb == value)
                {
                    return;
                }

                _sizeKb = value;
                OnPropertyChanged();
                OnPropertyChanged(nameof(SizeBytes));
                OnPropertyChanged(nameof(MetaText));
            }
        }

        public string Icon { get; set; } = string.Empty;

        public ProgramSource Source { get; set; } = ProgramSource.Registry;

        public string PackageFullName { get; set; } = string.Empty;

        public string PackageFamily { get; set; } = string.Empty;

        public string RegistryHive { get; set; } = string.Empty;

        public string RegistrySubkey { get; set; } = string.Empty;

        public bool Checked
        {
            get => _checked;
            set
            {
                if (_checked == value)
                {
                    return;
                }

                _checked = value;
                OnPropertyChanged();
            }
        }

        public ProgramStatus Status
        {
            get => _status;
            set
            {
                if (_status == value)
                {
                    return;
                }

                _status = value;
                OnPropertyChanged();
                OnPropertyChanged(nameof(StatusText));
                OnPropertyChanged(nameof(HasStatus));
            }
        }

        public bool IsStoreApp => Source == ProgramSource.Store;

        public long SizeBytes => Math.Max(0, SizeKb) * 1024L;

        public bool HasStatus => Status != ProgramStatus.Idle;

        public string StatusText
        {
            get
            {
                switch (Status)
                {
                    case ProgramStatus.Running:
                        return "Removing\u2026";
                    case ProgramStatus.Success:
                        return "Removed";
                    case ProgramStatus.Error:
                        return "Failed";
                    default:
                        return string.Empty;
                }
            }
        }

        public string MetaText
        {
            get
            {
                var size = SizeBytes > 0 ? Formatting.FormatSize(SizeBytes) : string.Empty;
                var version = Version.Length > 0 ? "v" + Version : string.Empty;
                return Formatting.JoinMeta(IsStoreApp ? "Store" : string.Empty, Publisher, version, size);
            }
        }

        public string Key
        {
            get
            {
                if (IsStoreApp)
                {
                    var package = PackageFullName.Length > 0 ? PackageFullName : Name.ToLowerInvariant();
                    return "store::" + package;
                }

                if (RegistrySubkey.Length > 0)
                {
                    return "registry::" + RegistryHive + "\\" + RegistrySubkey;
                }

                return "registry::" + Name.ToLowerInvariant() + "|" +
                       Version.ToLowerInvariant() + "|" + UninstallString.ToLowerInvariant();
            }
        }

        public event PropertyChangedEventHandler PropertyChanged;

        private void OnPropertyChanged([CallerMemberName] string name = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
        }
    }
}

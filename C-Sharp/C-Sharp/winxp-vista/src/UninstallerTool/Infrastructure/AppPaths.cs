using System;
using System.IO;

namespace UninstallerTool.Infrastructure
{
    internal static class AppPaths
    {
        public const string AppId = "UninstallerTool";

        private static readonly string RootDirectory = BuildRootDirectory();

        public static string AppDataDirectory => RootDirectory;

        public static string CacheDirectory => EnsureDirectory(Path.Combine(RootDirectory, "cache"));

        public static string LogDirectory => EnsureDirectory(Path.Combine(RootDirectory, "logs"));

        public static string BackupDirectory => EnsureDirectory(Path.Combine(RootDirectory, "backups"));

        public static string SettingsFile => Path.Combine(RootDirectory, "settings.ini");

        public static string StoreCacheFile => Path.Combine(CacheDirectory, "store_apps.json");

        public static string SizeCacheFile => Path.Combine(CacheDirectory, "folder_sizes.json");

        public static string LogFile => Path.Combine(LogDirectory, "app.log");

        private static string BuildRootDirectory()
        {
            var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            if (string.IsNullOrWhiteSpace(local))
            {
                local = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
                    "AppData",
                    "Local");
            }

            return EnsureDirectory(Path.Combine(local, AppId));
        }

        private static string EnsureDirectory(string path)
        {
            try
            {
                Directory.CreateDirectory(path);
            }
            catch (IOException)
            {
            }
            catch (UnauthorizedAccessException)
            {
            }

            return path;
        }
    }
}

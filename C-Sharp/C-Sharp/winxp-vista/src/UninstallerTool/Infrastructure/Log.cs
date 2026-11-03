using System;
using System.Globalization;
using System.IO;
using System.Text;

namespace UninstallerTool.Infrastructure
{
    internal static class Log
    {
        private const long MaxBytes = 1500000;
        private const int MaxBackups = 3;

        private static readonly object SyncRoot = new object();

        private static string _path;

        public static void Initialize()
        {
            _path = AppPaths.LogFile;
            Info("Starting application");
        }

        public static void Info(string message)
        {
            Write("INFO", message);
        }

        public static void Warn(string message)
        {
            Write("WARN", message);
        }

        public static void Error(string message)
        {
            Write("ERROR", message);
        }

        public static void Exception(string context, Exception exception)
        {
            Write("ERROR", context + Environment.NewLine + exception);
        }

        private static void Write(string level, string message)
        {
            if (string.IsNullOrEmpty(_path))
            {
                return;
            }

            var line = string.Format(
                CultureInfo.InvariantCulture,
                "{0}  {1,-8}  {2}",
                DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                level,
                message);

            lock (SyncRoot)
            {
                try
                {
                    Rotate();
                    File.AppendAllText(_path, line + Environment.NewLine, new UTF8Encoding(false));
                }
                catch (IOException)
                {
                }
                catch (UnauthorizedAccessException)
                {
                }
            }
        }

        private static void Rotate()
        {
            var file = new FileInfo(_path);
            if (!file.Exists || file.Length < MaxBytes)
            {
                return;
            }

            for (var index = MaxBackups - 1; index >= 1; index--)
            {
                var source = _path + "." + index.ToString(CultureInfo.InvariantCulture);
                var target = _path + "." + (index + 1).ToString(CultureInfo.InvariantCulture);
                if (!File.Exists(source))
                {
                    continue;
                }

                if (File.Exists(target))
                {
                    File.Delete(target);
                }

                File.Move(source, target);
            }

            var first = _path + ".1";
            if (File.Exists(first))
            {
                File.Delete(first);
            }

            File.Move(_path, first);
        }
    }
}

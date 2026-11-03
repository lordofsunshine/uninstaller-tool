using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;

namespace UninstallerTool.Infrastructure
{
    internal sealed class AppSettings
    {
        private readonly Dictionary<string, string> _values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        public AppSettings()
        {
            Load();
        }

        public double? WindowLeft { get; set; }

        public double? WindowTop { get; set; }

        public double? WindowWidth { get; set; }

        public double? WindowHeight { get; set; }

        public bool WindowMaximized { get; set; }

        public double SplitterRatio { get; set; } = 0.72;

        public int SortMode { get; set; }

        public bool SilentMode { get; set; }

        public void Load()
        {
            _values.Clear();
            string[] lines;
            try
            {
                if (!File.Exists(AppPaths.SettingsFile))
                {
                    return;
                }

                lines = File.ReadAllLines(AppPaths.SettingsFile, Encoding.UTF8);
            }
            catch (IOException)
            {
                return;
            }
            catch (UnauthorizedAccessException)
            {
                return;
            }

            foreach (var line in lines)
            {
                var trimmed = line.Trim();
                if (trimmed.Length == 0 || trimmed.StartsWith("[", StringComparison.Ordinal))
                {
                    continue;
                }

                var separator = trimmed.IndexOf('=');
                if (separator <= 0)
                {
                    continue;
                }

                var key = trimmed.Substring(0, separator).Trim();
                var value = trimmed.Substring(separator + 1).Trim();
                _values[key] = value;
            }

            WindowLeft = ReadDouble("window/left");
            WindowTop = ReadDouble("window/top");
            WindowWidth = ReadDouble("window/width");
            WindowHeight = ReadDouble("window/height");
            WindowMaximized = ReadBool("window/maximized");
            SplitterRatio = ReadDouble("window/splitter") ?? 0.72;
            SortMode = ReadInt("list/sort");
            SilentMode = ReadBool("uninstall/silent");
        }

        public void Save()
        {
            var builder = new StringBuilder();
            AppendDouble(builder, "window/left", WindowLeft);
            AppendDouble(builder, "window/top", WindowTop);
            AppendDouble(builder, "window/width", WindowWidth);
            AppendDouble(builder, "window/height", WindowHeight);
            builder.AppendLine("window/maximized=" + (WindowMaximized ? "1" : "0"));
            builder.AppendLine("window/splitter=" + SplitterRatio.ToString("0.####", CultureInfo.InvariantCulture));
            builder.AppendLine("list/sort=" + SortMode.ToString(CultureInfo.InvariantCulture));
            builder.AppendLine("uninstall/silent=" + (SilentMode ? "1" : "0"));

            try
            {
                File.WriteAllText(AppPaths.SettingsFile, builder.ToString(), new UTF8Encoding(false));
            }
            catch (IOException)
            {
            }
            catch (UnauthorizedAccessException)
            {
            }
        }

        private static void AppendDouble(StringBuilder builder, string key, double? value)
        {
            if (!value.HasValue)
            {
                return;
            }

            builder.AppendLine(key + "=" + value.Value.ToString("0.####", CultureInfo.InvariantCulture));
        }

        private double? ReadDouble(string key)
        {
            if (!_values.TryGetValue(key, out var raw) ||
                !double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var value))
            {
                return null;
            }

            return value;
        }

        private int ReadInt(string key)
        {
            if (!_values.TryGetValue(key, out var raw) ||
                !int.TryParse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out var value))
            {
                return 0;
            }

            return Math.Max(0, value);
        }

        private bool ReadBool(string key)
        {
            if (!_values.TryGetValue(key, out var raw))
            {
                return false;
            }

            var text = raw.Trim().ToLowerInvariant();
            return text == "1" || text == "true" || text == "yes";
        }
    }
}

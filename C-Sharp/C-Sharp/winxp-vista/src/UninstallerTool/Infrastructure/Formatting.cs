using System;
using System.Globalization;
using System.IO;
using System.Text.RegularExpressions;

namespace UninstallerTool.Infrastructure
{
    internal static class Formatting
    {
        private static readonly string[] Units = { "B", "KB", "MB", "GB", "TB", "PB" };

        private static readonly Regex NonWord = new Regex(@"[^\w]+", RegexOptions.Compiled);

        private static readonly Regex CompactDate = new Regex(@"^\d{8}$", RegexOptions.Compiled);

        private static readonly Regex IsoDate = new Regex(@"^\d{4}-\d{2}-\d{2}$", RegexOptions.Compiled);

        public static string FormatSize(double bytes)
        {
            var value = bytes > 0 ? bytes : 0d;
            for (var index = 0; index < Units.Length - 1; index++)
            {
                if (value < 1024)
                {
                    return string.Format(CultureInfo.InvariantCulture, "{0:0.00} {1}", value, Units[index]);
                }

                value /= 1024;
            }

            return string.Format(CultureInfo.InvariantCulture, "{0:0.00} {1}", value, Units[Units.Length - 1]);
        }

        public static string FormatInstallDate(string raw)
        {
            var text = (raw ?? string.Empty).Trim();
            if (text.Length == 0)
            {
                return string.Empty;
            }

            if (CompactDate.IsMatch(text) &&
                DateTime.TryParseExact(text, "yyyyMMdd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var compact))
            {
                return compact.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
            }

            if (IsoDate.IsMatch(text) &&
                DateTime.TryParseExact(text, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out var iso))
            {
                return iso.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
            }

            return text;
        }

        public static string NormalizeName(string value)
        {
            return NonWord.Replace((value ?? string.Empty).ToLowerInvariant(), string.Empty);
        }

        public static IconReference SplitIconReference(string raw)
        {
            var text = Environment.ExpandEnvironmentVariables((raw ?? string.Empty)).Trim();
            if (text.Length == 0)
            {
                return new IconReference(string.Empty, 0);
            }

            if (text[0] == '"')
            {
                var end = text.IndexOf('"', 1);
                if (end < 0)
                {
                    return new IconReference(text.Trim('"'), 0);
                }

                var path = text.Substring(1, end - 1);
                var rest = text.Substring(end + 1).Trim();
                if (rest.StartsWith(",", StringComparison.Ordinal) &&
                    int.TryParse(rest.Substring(1).Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var quotedIndex))
                {
                    return new IconReference(path, quotedIndex);
                }

                return new IconReference(path, 0);
            }

            var comma = text.LastIndexOf(',');
            if (comma > 0 &&
                int.TryParse(text.Substring(comma + 1).Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var index))
            {
                return new IconReference(text.Substring(0, comma).Trim().Trim('"'), index);
            }

            return new IconReference(text.Trim('"'), 0);
        }

        public static string JoinMeta(params string[] parts)
        {
            var builder = new System.Collections.Generic.List<string>(parts.Length);
            foreach (var part in parts)
            {
                if (!string.IsNullOrWhiteSpace(part))
                {
                    builder.Add(part);
                }
            }

            return string.Join("   \u00b7   ", builder);
        }

        public static bool IsFile(string path)
        {
            try
            {
                return !string.IsNullOrWhiteSpace(path) && File.Exists(path);
            }
            catch (IOException)
            {
                return false;
            }
            catch (UnauthorizedAccessException)
            {
                return false;
            }
        }
    }

    internal readonly struct IconReference
    {
        public IconReference(string path, int index)
        {
            Path = path ?? string.Empty;
            Index = index;
        }

        public string Path { get; }

        public int Index { get; }
    }
}

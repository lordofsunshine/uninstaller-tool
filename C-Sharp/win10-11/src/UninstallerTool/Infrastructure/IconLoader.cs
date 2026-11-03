using System;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media.Imaging;

namespace UninstallerTool.Infrastructure
{
    internal static class IconLoader
    {
        private static readonly Dictionary<string, BitmapSource> Cache =
            new Dictionary<string, BitmapSource>(StringComparer.OrdinalIgnoreCase);

        public static BitmapSource Load(string rawIcon, int size = 32)
        {
            var reference = Formatting.SplitIconReference(rawIcon);
            if (!Formatting.IsFile(reference.Path))
            {
                return null;
            }

            var key = reference.Path + "|" + reference.Index + "|" + size;
            if (Cache.TryGetValue(key, out var cached))
            {
                return cached;
            }

            BitmapSource image = null;
            var handle = NativeMethods.ExtractIcon(reference.Path, reference.Index, size);
            if (handle != IntPtr.Zero)
            {
                try
                {
                    image = Imaging.CreateBitmapSourceFromHIcon(
                        handle,
                        Int32Rect.Empty,
                        BitmapSizeOptions.FromEmptyOptions());
                    image.Freeze();
                }
                catch (ArgumentException)
                {
                }
                catch (System.Runtime.InteropServices.COMException)
                {
                }
                finally
                {
                    NativeMethods.ReleaseIcon(handle);
                }
            }

            Cache[key] = image;
            return image;
        }
    }
}

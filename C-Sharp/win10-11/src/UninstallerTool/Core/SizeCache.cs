using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.Serialization.Json;
using UninstallerTool.Infrastructure;

namespace UninstallerTool.Core
{
    [System.Runtime.Serialization.DataContract]
    public sealed class SizeCacheEntry
    {
        [System.Runtime.Serialization.DataMember(Name = "path")]
        public string Path { get; set; }

        [System.Runtime.Serialization.DataMember(Name = "mtime")]
        public long Modified { get; set; }

        [System.Runtime.Serialization.DataMember(Name = "size")]
        public long Size { get; set; }
    }

    [System.Runtime.Serialization.DataContract]
    public sealed class SizeCacheDto
    {
        [System.Runtime.Serialization.DataMember(Name = "entries")]
        public SizeCacheEntry[] Entries { get; set; }
    }

    internal sealed class SizeCache
    {
        private readonly Dictionary<string, SizeCacheEntry> _entries =
            new Dictionary<string, SizeCacheEntry>(StringComparer.Ordinal);

        private bool _dirty;

        public SizeCache()
        {
            Load();
        }

        public long? Get(string directory)
        {
            var key = Safety.NormalizePath(directory);
            if (key.Length == 0 || !_entries.TryGetValue(key, out var entry))
            {
                return null;
            }

            if (entry.Modified != FileSystemService.DirectoryStamp(key))
            {
                return null;
            }

            return Math.Max(0, entry.Size);
        }

        public void Put(string directory, long size)
        {
            var key = Safety.NormalizePath(directory);
            if (key.Length == 0)
            {
                return;
            }

            _entries[key] = new SizeCacheEntry
            {
                Path = key,
                Modified = FileSystemService.DirectoryStamp(key),
                Size = Math.Max(0, size)
            };
            _dirty = true;
        }

        public void Save()
        {
            if (!_dirty)
            {
                return;
            }

            var temporary = AppPaths.SizeCacheFile + ".tmp";
            try
            {
                using (var stream = File.Create(temporary))
                {
                    var serializer = new DataContractJsonSerializer(typeof(SizeCacheDto));
                    serializer.WriteObject(stream, new SizeCacheDto { Entries = _entries.Values.ToArray() });
                }

                if (File.Exists(AppPaths.SizeCacheFile))
                {
                    File.Delete(AppPaths.SizeCacheFile);
                }

                File.Move(temporary, AppPaths.SizeCacheFile);
                _dirty = false;
            }
            catch (IOException exception)
            {
                Log.Warn("Could not save the folder size cache: " + exception.Message);
                TryDelete(temporary);
            }
            catch (UnauthorizedAccessException exception)
            {
                Log.Warn("Could not save the folder size cache: " + exception.Message);
                TryDelete(temporary);
            }
        }

        public long Measure(UninstallerTool.Models.ProgramEntry program, Func<bool> cancelled)
        {
            var directory = program.InstallLocation;
            if (!Safety.IsSafeProgramDirectory(directory))
            {
                return 0;
            }

            var cached = Get(directory);
            if (cached.HasValue)
            {
                return cached.Value;
            }

            var size = FileSystemService.MeasureDirectorySize(directory, cancelled);
            Put(directory, size);
            return size;
        }

        private void Load()
        {
            try
            {
                if (!File.Exists(AppPaths.SizeCacheFile))
                {
                    return;
                }

                SizeCacheDto payload;
                using (var stream = File.OpenRead(AppPaths.SizeCacheFile))
                {
                    var serializer = new DataContractJsonSerializer(typeof(SizeCacheDto));
                    payload = serializer.ReadObject(stream) as SizeCacheDto;
                }

                if (payload?.Entries == null)
                {
                    return;
                }

                foreach (var entry in payload.Entries)
                {
                    if (string.IsNullOrWhiteSpace(entry.Path))
                    {
                        continue;
                    }

                    _entries[entry.Path] = entry;
                }
            }
            catch (IOException)
            {
            }
            catch (UnauthorizedAccessException)
            {
            }
            catch (System.Runtime.Serialization.SerializationException)
            {
            }
        }

        private static void TryDelete(string path)
        {
            try
            {
                if (File.Exists(path))
                {
                    File.Delete(path);
                }
            }
            catch (IOException)
            {
            }
            catch (UnauthorizedAccessException)
            {
            }
        }
    }
}

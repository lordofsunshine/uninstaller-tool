using System.Threading;

namespace System
{
    public sealed class Progress<T> : IProgress<T>
    {
        private readonly Action<T> _handler;
        private readonly SynchronizationContext _context;

        public Progress(Action<T> handler)
        {
            _handler = handler ?? throw new ArgumentNullException(nameof(handler));
            _context = SynchronizationContext.Current;
        }

        public void Report(T value)
        {
            if (_context != null)
            {
                _context.Post(state => _handler((T)state), value);
                return;
            }

            _handler(value);
        }
    }
}

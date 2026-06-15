using System.Diagnostics;
using OpenCvSharp;

namespace PrismKenz.App.Camera;

public sealed class CameraCapture : IDisposable
{
    private readonly VideoCapture _capture;
    private readonly bool _threaded;
    private readonly object _frameLock = new();
    private readonly ManualResetEventSlim _firstFrameReady = new(false);
    private readonly Thread? _captureThread;
    private Mat? _latestFrame;
    private volatile bool _stopping;
    private volatile bool _captureFailed;
    private double _captureWaitReadMs;
    private bool _hasCaptureTiming;

    public double CaptureWaitReadMilliseconds => Volatile.Read(ref _captureWaitReadMs);

    public CameraCapture(AppConfig config)
    {
        var requestedBackend = ResolveBackend(config.CameraBackend);
        _capture = OpenCamera(config.CameraIndex, requestedBackend);
        ConfigureCapture(config);
        LogCaptureConfiguration(config, requestedBackend);

        _threaded = config.UseThreadedCapture;
        if (_threaded)
        {
            _captureThread = new Thread(CaptureLoop)
            {
                IsBackground = true,
                Name = "PrismKenz.CameraCapture",
            };
            _captureThread.Start();

            if (!_firstFrameReady.Wait(TimeSpan.FromSeconds(5)) || _captureFailed)
            {
                Dispose();
                throw new InvalidOperationException(
                    "A thread de captura nao conseguiu obter o primeiro frame.");
            }

            Console.WriteLine("[Camera] Captura threaded latest-frame ativada.");
        }
    }

    public bool TryRead(out Mat frame)
    {
        if (!_threaded)
        {
            frame = new Mat();
            var startedAt = Stopwatch.GetTimestamp();
            var success = _capture.Read(frame) && !frame.Empty();
            UpdateCaptureTiming(Stopwatch.GetElapsedTime(startedAt).TotalMilliseconds);

            if (success)
            {
                return true;
            }

            frame.Dispose();
            frame = null!;
            return false;
        }

        lock (_frameLock)
        {
            if (_captureFailed || _latestFrame is null || _latestFrame.Empty())
            {
                frame = null!;
                return false;
            }

            frame = _latestFrame.Clone();
            return true;
        }
    }

    private void CaptureLoop()
    {
        try
        {
            while (!_stopping)
            {
                using var capturedFrame = new Mat();
                var startedAt = Stopwatch.GetTimestamp();
                var success = _capture.Read(capturedFrame) && !capturedFrame.Empty();
                UpdateCaptureTiming(
                    Stopwatch.GetElapsedTime(startedAt).TotalMilliseconds);

                if (!success)
                {
                    _captureFailed = true;
                    _firstFrameReady.Set();
                    return;
                }

                var publishedFrame = capturedFrame.Clone();

                lock (_frameLock)
                {
                    var previousFrame = _latestFrame;
                    _latestFrame = publishedFrame;
                    previousFrame?.Dispose();
                }

                _firstFrameReady.Set();
            }
        }
        catch (Exception exception)
        {
            if (!_stopping)
            {
                Console.WriteLine($"[Camera] Erro na thread de captura: {exception.Message}");
            }

            _captureFailed = true;
            _firstFrameReady.Set();
        }
    }

    private static VideoCapture OpenCamera(int cameraIndex, VideoCaptureAPIs backend)
    {
        var capture = new VideoCapture();

        if (capture.Open(cameraIndex, backend))
        {
            return capture;
        }

        capture.Release();
        Console.WriteLine(
            $"[Camera] AVISO: backend {backend} falhou. Tentando backend automatico.");

        if (capture.Open(cameraIndex, VideoCaptureAPIs.ANY))
        {
            return capture;
        }

        capture.Dispose();
        throw new InvalidOperationException(
            $"Nao foi possivel abrir a camera de indice {cameraIndex}.");
    }

    private void ConfigureCapture(AppConfig config)
    {
        var fourCc = NormalizeFourCc(config.CameraFourCC);
        _capture.Set(
            VideoCaptureProperties.FourCC,
            VideoWriter.FourCC(fourCc[0], fourCc[1], fourCc[2], fourCc[3]));
        _capture.Set(VideoCaptureProperties.FrameWidth, config.Width);
        _capture.Set(VideoCaptureProperties.FrameHeight, config.Height);
        _capture.Set(VideoCaptureProperties.Fps, config.Fps);
        _capture.Set(VideoCaptureProperties.BufferSize, Math.Max(1, config.CameraBufferSize));
    }

    private void LogCaptureConfiguration(AppConfig config, VideoCaptureAPIs requestedBackend)
    {
        var realFourCc = DecodeFourCc(_capture.Get(VideoCaptureProperties.FourCC));
        var backendName = GetBackendName();

        Console.WriteLine($"[Camera] Backend pedido: {requestedBackend}");
        Console.WriteLine($"[Camera] Backend usado: {backendName}");
        Console.WriteLine($"[Camera] Resolucao pedida: {config.Width}x{config.Height}");
        Console.WriteLine(
            $"[Camera] Resolucao real: {_capture.FrameWidth:0}x{_capture.FrameHeight:0}");
        Console.WriteLine($"[Camera] FPS pedido: {config.Fps}");
        Console.WriteLine($"[Camera] FPS real: {_capture.Fps:0.##}");
        Console.WriteLine($"[Camera] FOURCC real: {realFourCc}");
    }

    private string GetBackendName()
    {
        try
        {
            return _capture.GetBackendName();
        }
        catch
        {
            return "indisponivel";
        }
    }

    private void UpdateCaptureTiming(double elapsedMs)
    {
        if (_hasCaptureTiming)
        {
            var current = Volatile.Read(ref _captureWaitReadMs);
            Volatile.Write(ref _captureWaitReadMs, (current * 0.90) + (elapsedMs * 0.10));
        }
        else
        {
            Volatile.Write(ref _captureWaitReadMs, elapsedMs);
            _hasCaptureTiming = true;
        }
    }

    private static VideoCaptureAPIs ResolveBackend(string configuredBackend)
    {
        if (configuredBackend.Equals("MSMF", StringComparison.OrdinalIgnoreCase))
        {
            return VideoCaptureAPIs.MSMF;
        }

        if (!configuredBackend.Equals("DSHOW", StringComparison.OrdinalIgnoreCase))
        {
            Console.WriteLine(
                $"[Camera] AVISO: backend '{configuredBackend}' desconhecido. Usando DSHOW.");
        }

        return VideoCaptureAPIs.DSHOW;
    }

    private static string NormalizeFourCc(string configuredFourCc)
    {
        var fourCc = configuredFourCc.Trim().ToUpperInvariant();
        if (fourCc.Length == 4)
        {
            return fourCc;
        }

        Console.WriteLine(
            $"[Camera] AVISO: FOURCC '{configuredFourCc}' invalido. Usando MJPG.");
        return "MJPG";
    }

    private static string DecodeFourCc(double value)
    {
        var code = (int)value;
        if (code == 0)
        {
            return "indisponivel";
        }

        return new string(
        [
            (char)(code & 0xFF),
            (char)((code >> 8) & 0xFF),
            (char)((code >> 16) & 0xFF),
            (char)((code >> 24) & 0xFF),
        ]);
    }

    public void Dispose()
    {
        if (_stopping)
        {
            return;
        }

        _stopping = true;

        if (_captureThread is not null &&
            _captureThread.IsAlive &&
            Thread.CurrentThread != _captureThread)
        {
            if (!_captureThread.Join(TimeSpan.FromSeconds(2)))
            {
                _capture.Release();
                _captureThread.Join(TimeSpan.FromSeconds(1));
            }
        }

        _capture.Release();

        lock (_frameLock)
        {
            _latestFrame?.Dispose();
            _latestFrame = null;
        }

        if (_captureThread is null || !_captureThread.IsAlive)
        {
            _firstFrameReady.Dispose();
        }

        _capture.Dispose();
    }
}

using System.Text.Json;

namespace PrismKenz.App;

public sealed class AppConfig
{
    public int CameraIndex { get; init; } = 0;
    public int Width { get; init; } = 1280;
    public int Height { get; init; } = 720;
    public int Fps { get; init; } = 30;
    public string CameraBackend { get; init; } = "DSHOW";
    public string CameraFourCC { get; init; } = "MJPG";
    public bool UseThreadedCapture { get; init; } = true;
    public int CameraBufferSize { get; init; } = 1;
    public bool MirrorCamera { get; init; } = true;
    public bool BeautyEnabled { get; init; }
    public double BeautyStrength { get; init; } = 0.35;
    public bool BackgroundEnabled { get; init; }
    public string BackgroundMode { get; init; } = "none";
    public string BackgroundImagePath { get; init; } = "assets/backgrounds/bg.jpg";
    public bool ShowPerformanceLogs { get; init; } = true;
    public double FpsLogIntervalSeconds { get; init; } = 2.0;

    public static AppConfig Load(string? path = null)
    {
        path ??= Path.Combine(AppContext.BaseDirectory, "appsettings.json");

        if (!File.Exists(path))
        {
            Console.WriteLine($"[Config] {path} nao encontrado. Usando valores padrao.");
            return new AppConfig();
        }

        var json = File.ReadAllText(path);
        var config = JsonSerializer.Deserialize<AppConfig>(
            json,
            new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

        return config ?? throw new InvalidOperationException(
            "Nao foi possivel carregar appsettings.json.");
    }
}

using OpenCvSharp;

namespace PrismKenz.App.Effects;

public sealed class BackgroundEffect : IDisposable
{
    private readonly AppConfig _config;
    private Mat? _cachedImage;
    private Size _cachedImageSize;
    private bool _missingImageWarningShown;

    public BackgroundEffect(AppConfig config)
    {
        _config = config;
    }

    public bool IsActive =>
        _config.BackgroundEnabled &&
        !_config.BackgroundMode.Equals("none", StringComparison.OrdinalIgnoreCase);

    public Mat? Prepare(Mat frame)
    {
        if (!IsActive)
        {
            return null;
        }

        if (_config.BackgroundMode.Equals("blur", StringComparison.OrdinalIgnoreCase))
        {
            var blurred = new Mat();
            Cv2.GaussianBlur(frame, blurred, new Size(31, 31), 0);
            return blurred;
        }

        if (_config.BackgroundMode.Equals("image", StringComparison.OrdinalIgnoreCase))
        {
            return PrepareImage(frame.Size());
        }

        return null;
    }

    public Mat Compose(Mat foreground, Mat background, Mat alpha)
    {
        using var normalizedAlpha = EnsureFloatAlpha(alpha);
        using var inverseAlpha = new Mat();
        Cv2.Subtract(Scalar.All(1.0), normalizedAlpha, inverseAlpha);

        var output = new Mat();
        Cv2.BlendLinear(foreground, background, normalizedAlpha, inverseAlpha, output);
        return output;
    }

    private Mat? PrepareImage(Size size)
    {
        if (_cachedImage is not null && _cachedImageSize == size)
        {
            return _cachedImage.Clone();
        }

        var path = ResolvePath(_config.BackgroundImagePath);
        using var image = Cv2.ImRead(path);

        if (image.Empty())
        {
            if (!_missingImageWarningShown)
            {
                Console.WriteLine($"[Background] Imagem nao encontrada: {path}");
                _missingImageWarningShown = true;
            }

            return null;
        }

        _cachedImage?.Dispose();
        _cachedImage = new Mat();
        Cv2.Resize(image, _cachedImage, size, interpolation: InterpolationFlags.Area);
        _cachedImageSize = size;
        return _cachedImage.Clone();
    }

    private static Mat EnsureFloatAlpha(Mat alpha)
    {
        if (alpha.Type() == MatType.CV_32FC1)
        {
            return alpha.Clone();
        }

        var normalized = new Mat();
        alpha.ConvertTo(normalized, MatType.CV_32FC1, 1.0 / 255.0);
        return normalized;
    }

    private static string ResolvePath(string configuredPath)
    {
        if (Path.IsPathRooted(configuredPath))
        {
            return configuredPath;
        }

        var currentDirectoryPath = Path.GetFullPath(configuredPath);
        if (File.Exists(currentDirectoryPath))
        {
            return currentDirectoryPath;
        }

        return Path.Combine(AppContext.BaseDirectory, configuredPath);
    }

    public void Dispose()
    {
        _cachedImage?.Dispose();
    }
}

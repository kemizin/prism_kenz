using OpenCvSharp;

namespace PrismKenz.App.Effects;

public sealed class BeautyEffect
{
    private readonly bool _enabled;
    private readonly double _strength;

    public BeautyEffect(AppConfig config)
    {
        _enabled = config.BeautyEnabled;
        _strength = Math.Clamp(config.BeautyStrength, 0.0, 1.0);
    }

    public void Apply(Mat frame)
    {
        if (!_enabled || _strength <= 0)
        {
            return;
        }

        using var smooth = new Mat();
        Cv2.GaussianBlur(frame, smooth, new Size(5, 5), 0);
        Cv2.AddWeighted(frame, 1.0 - _strength, smooth, _strength, 0, frame);
    }
}

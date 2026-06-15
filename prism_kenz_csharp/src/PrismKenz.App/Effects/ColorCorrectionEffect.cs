using OpenCvSharp;

namespace PrismKenz.App.Effects;

public sealed class ColorCorrectionEffect
{
    public void Apply(Mat frame)
    {
        Cv2.ConvertScaleAbs(frame, frame, alpha: 1.02, beta: 1.0);
    }
}

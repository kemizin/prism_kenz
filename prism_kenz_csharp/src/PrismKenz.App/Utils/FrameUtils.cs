using OpenCvSharp;

namespace PrismKenz.App.Utils;

public static class FrameUtils
{
    public static Mat CloneOrMirror(Mat frame, bool mirror)
    {
        if (!mirror)
        {
            return frame.Clone();
        }

        var mirrored = new Mat();
        Cv2.Flip(frame, mirrored, FlipMode.Y);
        return mirrored;
    }
}

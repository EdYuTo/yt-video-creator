// Person-segmentation matte, computed locally with Apple Vision.
//
//   segment_person <in.mp4> <out_matte.mp4>
//
// Reads every frame with AVAssetReader, runs VNGeneratePersonSegmentationRequest (.accurate) through one
// VNSequenceRequestHandler (temporal stability), scales the matte up to the frame size and writes it as a
// grayscale H.264 video with the same size, frame count and timestamps (so the same fps).
// It writes to a hidden .<name>.partial.mp4 beside the output and renames it on success, so a failed or
// interrupted run (error, SIGINT, SIGTERM) never leaves a partial matte under the real name.
// Built by bubble.py: swiftc -O segment_person.swift -o ~/.cache/yt-video-creator/bin/segment_person
import AVFoundation
import Accelerate
import CoreVideo
import Foundation
import Vision

let args = CommandLine.arguments
guard args.count == 3 else {
    FileHandle.standardError.write("usage: segment_person <in.mp4> <out_matte.mp4>\n".data(using: .utf8)!)
    exit(2)
}
let inURL = URL(fileURLWithPath: args[1])
let outURL = URL(fileURLWithPath: args[2])
let tmpURL = outURL.deletingLastPathComponent()
    .appendingPathComponent("." + outURL.deletingPathExtension().lastPathComponent + ".partial.mp4")
let tmpPath = strdup(tmpURL.path)!  // C string, so the signal handlers can unlink it

func fail(_ msg: String) -> Never {
    unlink(tmpPath)
    FileHandle.standardError.write(("segment_person: " + msg + "\n").data(using: .utf8)!)
    exit(1)
}
for sig in [SIGINT, SIGTERM] {
    signal(sig) { s in
        unlink(tmpPath)
        _exit(128 + s)
    }
}
unlink(tmpPath)  // a leftover from a killed run

func run() async throws {
    let asset = AVURLAsset(url: inURL)
    guard let track = try await asset.loadTracks(withMediaType: .video).first else { fail("no video track in \(args[1])") }
    let reader = try AVAssetReader(asset: asset)
    let readerOut = AVAssetReaderTrackOutput(
        track: track, outputSettings: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
    readerOut.alwaysCopiesSampleData = false
    reader.add(readerOut)
    guard reader.startReading() else { fail("cannot read \(args[1]): \(String(describing: reader.error))") }

    let request = VNGeneratePersonSegmentationRequest()
    request.qualityLevel = .accurate
    request.outputPixelFormat = kCVPixelFormatType_OneComponent8
    let handler = VNSequenceRequestHandler()

    var writer: AVAssetWriter!
    var input: AVAssetWriterInput!
    var adaptor: AVAssetWriterInputPixelBufferAdaptor!
    var gray = vImage_Buffer()  // matte scaled to the frame size
    var frames = 0

    while let sample = readerOut.copyNextSampleBuffer() {
        guard let frame = CMSampleBufferGetImageBuffer(sample) else { continue }
        let pts = CMSampleBufferGetPresentationTimeStamp(sample)
        let w = CVPixelBufferGetWidth(frame), h = CVPixelBufferGetHeight(frame)

        if writer == nil {
            writer = try AVAssetWriter(outputURL: tmpURL, fileType: .mp4)
            input = AVAssetWriterInput(mediaType: .video, outputSettings: [
                AVVideoCodecKey: AVVideoCodecType.h264,
                AVVideoWidthKey: w,
                AVVideoHeightKey: h,
                AVVideoColorPropertiesKey: [
                    AVVideoColorPrimariesKey: AVVideoColorPrimaries_ITU_R_709_2,
                    AVVideoTransferFunctionKey: AVVideoTransferFunction_ITU_R_709_2,
                    AVVideoYCbCrMatrixKey: AVVideoYCbCrMatrix_ITU_R_709_2,
                ],
                AVVideoCompressionPropertiesKey: [
                    // High bitrate so the soft matte edges don't band.
                    AVVideoAverageBitRateKey: max(20_000_000, w * h * 10),
                    AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
                ],
            ])
            input.expectsMediaDataInRealTime = false
            adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
                kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
                kCVPixelBufferWidthKey as String: w,
                kCVPixelBufferHeightKey as String: h,
            ])
            writer.add(input)
            guard writer.startWriting() else { fail("cannot write \(args[2]): \(String(describing: writer.error))") }
            writer.startSession(atSourceTime: pts)
            gray = try vImage_Buffer(width: w, height: h, bitsPerPixel: 8)
        }

        try handler.perform([request], on: frame)
        guard let matte = request.results?.first?.pixelBuffer else { fail("no matte for frame \(frames)") }

        // Scale the (smaller) matte up to the frame size.
        CVPixelBufferLockBaseAddress(matte, .readOnly)
        var src = vImage_Buffer(data: CVPixelBufferGetBaseAddress(matte),
                                height: vImagePixelCount(CVPixelBufferGetHeight(matte)),
                                width: vImagePixelCount(CVPixelBufferGetWidth(matte)),
                                rowBytes: CVPixelBufferGetBytesPerRow(matte))
        let scaled = vImageScale_Planar8(&src, &gray, nil, vImage_Flags(kvImageNoFlags))
        CVPixelBufferUnlockBaseAddress(matte, .readOnly)
        guard scaled == kvImageNoError else { fail("vImageScale failed (\(scaled))") }

        // Gray -> BGRA (B = G = R = matte); the encoder turns it into luma.
        var out: CVPixelBuffer?
        guard let pool = adaptor.pixelBufferPool,
              CVPixelBufferPoolCreatePixelBuffer(nil, pool, &out) == kCVReturnSuccess, let out else {
            fail("no output pixel buffer")
        }
        CVPixelBufferLockBaseAddress(out, [])
        var dst = vImage_Buffer(data: CVPixelBufferGetBaseAddress(out), height: vImagePixelCount(h),
                                width: vImagePixelCount(w), rowBytes: CVPixelBufferGetBytesPerRow(out))
        let conv = vImageConvert_Planar8toARGB8888(&gray, &gray, &gray, &gray, &dst, vImage_Flags(kvImageNoFlags))
        CVPixelBufferUnlockBaseAddress(out, [])
        guard conv == kvImageNoError else { fail("vImageConvert failed (\(conv))") }

        while !input.isReadyForMoreMediaData { usleep(1000) }
        guard adaptor.append(out, withPresentationTime: pts) else {
            fail("append failed at frame \(frames): \(String(describing: writer.error))")
        }
        frames += 1
    }

    guard reader.status == .completed else { fail("reading stopped: \(String(describing: reader.error))") }
    guard frames > 0 else { fail("no frames in \(args[1])") }
    input.markAsFinished()
    await writer.finishWriting()
    guard writer.status == .completed else { fail("writing failed: \(String(describing: writer.error))") }
    free(gray.data)
    guard rename(tmpPath, outURL.path) == 0 else { fail("cannot rename to \(args[2]): \(String(cString: strerror(errno)))") }
    print("segment_person: \(frames) frames -> \(args[2])")
}

do {
    try await run()
} catch {
    fail("\(error)")
}

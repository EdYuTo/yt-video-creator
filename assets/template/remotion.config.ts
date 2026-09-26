import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
// YouTube master: H.264, high quality (YouTube re-encodes anyway, so feed it a clean source).
Config.setCodec('h264');
Config.setCrf(16);

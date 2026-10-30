import { qrcodegen } from './vendor/qrcodegen.mjs';

// Local QR encoding only. Never send the provisioning URI to another service, log it or turn it into HTML.
export function makeQrModules(otpauth: string): boolean[][] {
  if (typeof otpauth !== 'string' || otpauth.length > 4096) throw new Error('mfa_qr_invalid');
  let uri: URL;
  try { uri = new URL(otpauth); } catch { throw new Error('mfa_qr_invalid'); }
  if (uri.protocol !== 'otpauth:' || uri.hostname !== 'totp' || !uri.searchParams.get('secret')) throw new Error('mfa_qr_invalid');
  try {
    const qr = qrcodegen.QrCode.encodeText(otpauth, qrcodegen.QrCode.Ecc.MEDIUM);
    return Array.from({ length: qr.size }, (_, y) => Array.from({ length: qr.size }, (_, x) => qr.getModule(x, y)));
  } catch { throw new Error('mfa_qr_invalid'); }
}

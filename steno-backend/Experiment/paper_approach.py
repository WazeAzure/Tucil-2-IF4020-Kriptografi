#!/usr/bin/env python3
"""
MP3 LSB Steganography implementation (class MP3Stego)

Requirements:
 - pydub (pip install pydub)
 - numpy (pip install numpy)
 - ffmpeg installed and on PATH for pydub to load/export mp3

This script implements embedding (encode) and extraction (decode)
according to the methodology described in the user's research-paper summary.

Usage example is at the bottom under if __name__ == "__main__".
"""

import os
import math
import random
from typing import Tuple
from pydub import AudioSegment
import numpy as np


class MP3Stego:
    """
    MP3 LSB steganography class.

    Methods:
      - embed(input_mp3_path, input_text_path, output_mp3_path, lsb_bits)
      - extract(input_mp3_path, output_text_path, lsb_bits)
    """

    def __init__(self):
        # constant used in normalization / denormalization steps from the paper
        self._NORMALIZE_SCALE = 1_000_000

    # ---------------------------
    # Utility / conversion helpers
    # ---------------------------
    def _load_mp3_as_float_samples(self, path: str) -> Tuple[np.ndarray, int, int, int]:
        """
        Load MP3 using pydub and return:
          - samples: numpy array of shape (num_samples, channels) of floats in [-1.0, 1.0]
          - frame_rate (sample rate)
          - channels
          - sample_width (bytes)
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(f"MP3 file not found: {path}")

        audio = AudioSegment.from_file(path)
        frame_rate = audio.frame_rate
        channels = audio.channels
        sample_width = audio.sample_width  # bytes per sample (1, 2, 3, or 4)

        # pydub's get_array_of_samples returns interleaved ints
        arr = np.array(audio.get_array_of_samples())

        # reshape to (n_frames, channels)
        if channels > 1:
            arr = arr.reshape((-1, channels))
        else:
            arr = arr.reshape((-1, 1))

        # determine integer dtype and divisor for normalization to [-1,1]
        if sample_width == 1:
            dtype = np.int8
            max_abs = float(2 ** 7)  # 128
        elif sample_width == 2:
            dtype = np.int16
            max_abs = float(2 ** 15)  # 32768
        elif sample_width == 3:
            # 24-bit packed - convert to int32 properly
            # pydub already returns 32-bit-like ints for 24-bit files in get_array_of_samples,
            # but we can't assume. We'll cast to int32 and compute divisor as 2**23
            dtype = np.int32
            max_abs = float(2 ** 23)
        elif sample_width == 4:
            dtype = np.int32
            max_abs = float(2 ** 31)
        else:
            raise ValueError(f"Unsupported sample width: {sample_width} bytes")

        arr = arr.astype(np.float64)

        # Normalize to [-1, 1)
        # For signed PCM:
        arr /= max_abs

        return arr, frame_rate, channels, sample_width

    def _samples_float_to_int_pcm(self, floats: np.ndarray, sample_width: int) -> np.ndarray:
        """
        Convert float samples in [-1,1) back to integer PCM samples depending on sample_width.
        returns an array of dtype appropriate (int16/int32/int8).
        """
        if sample_width == 1:
            max_abs = float(2 ** 7)
            dtype = np.int8
        elif sample_width == 2:
            max_abs = float(2 ** 15)
            dtype = np.int16
        elif sample_width == 3:
            max_abs = float(2 ** 23)
            dtype = np.int32  # we'll store as 32-bit for pydub
        elif sample_width == 4:
            max_abs = float(2 ** 31)
            dtype = np.int32
        else:
            raise ValueError(f"Unsupported sample width: {sample_width} bytes")

        scaled = floats * max_abs
        # Clip to valid range
        min_val = -max_abs
        max_val = max_abs - 1
        scaled = np.clip(scaled, min_val, max_val)
        return scaled.astype(dtype)

    def _int_array_to_audiosegment(self, arr: np.ndarray, frame_rate: int, channels: int, sample_width: int) -> AudioSegment:
        """
        Given an interleaved integer numpy array shaped (n_frames, channels)
        and audio params, build a pydub.AudioSegment for export.
        """
        # ensure interleaved shape
        if arr.ndim == 2 and arr.shape[1] == channels:
            interleaved = arr.flatten()  # interleave row-wise (pydub expects interleaved)
        elif arr.ndim == 1 and channels == 1:
            interleaved = arr
        else:
            raise ValueError("Array shape doesn't match channels")

        # pydub expects raw bytes little-endian for PCM
        raw_bytes = interleaved.tobytes()

        segment = AudioSegment(
            data=raw_bytes,
            sample_width=sample_width,
            frame_rate=frame_rate,
            channels=channels
        )
        return segment

    # ---------------------------
    # Signature generation helper
    # ---------------------------
    def _signatures_for_lsb(self, lsb_bits: int) -> Tuple[str, str]:
        """
        Return (start_signature, end_signature) strings of bits for given lsb_bits.
        The paper specified:
          - 1-bit: Start/End = '10101010101010'
          - 2-bit: Start/End = '01010101010101'
        For 3- and 4-bit we create unique patterns (must be unique & not too short).
        If paper's exact Table 2 values are available, replace them here.
        """
        if lsb_bits == 1:
            sig = '10101010101010'
            return sig, sig
        elif lsb_bits == 2:
            sig = '01010101010101'
            return sig, sig
        elif lsb_bits == 3:
            # Assume a distinctive 15-bit pattern for 3-bit LSB
            sig = '111000111000111'  # example distinct repeating pattern
            return sig, sig
        elif lsb_bits == 4:
            # Assume a distinctive 16-bit pattern for 4-bit LSB
            sig = '0011001100110011'
            return sig, sig
        else:
            raise ValueError("lsb_bits must be 1,2,3, or 4")

    # ---------------------------
    # Text -> bitstream & reverse
    # ---------------------------
    def _text_to_bitstream(self, text: str) -> str:
        """Convert ASCII text to a contiguous bitstream string ('010101...') using 8-bit ASCII."""
        bits = ''.join(f"{ord(c):08b}" for c in text)
        return bits

    def _bitstream_to_text(self, bitstream: str) -> str:
        """Convert a bitstream (length multiple of 8) to text by 8-bit ASCII chunks."""
        if len(bitstream) % 8 != 0:
            # Ignore incomplete trailing bits (shouldn't happen if embedding is correct)
            bitstream = bitstream[:len(bitstream) - (len(bitstream) % 8)]
        chars = [chr(int(bitstream[i:i+8], 2)) for i in range(0, len(bitstream), 8)]
        return ''.join(chars)

    # ---------------------------
    # Embedding
    # ---------------------------
    def embed(self, input_mp3_path: str, input_text_path: str, output_mp3_path: str, lsb_bits: int = 1):
        """
        Embed a text message (from input_text_path) into an MP3 (input_mp3_path),
        saving the stego MP3 to output_mp3_path, using lsb_bits LSBs (1-4).
        """
        # read secret message
        if not os.path.isfile(input_text_path):
            raise FileNotFoundError(f"Text file not found: {input_text_path}")
        with open(input_text_path, 'r', encoding='utf-8', errors='replace') as f:
            message = f.read()

        # convert message to bitstream
        message_bits = self._text_to_bitstream(message)

        # load mp3 and get float samples
        floats, frame_rate, channels, sample_width = self._load_mp3_as_float_samples(input_mp3_path)
        num_frames = floats.shape[0]
        num_samples = num_frames * channels  # total samples (interleaved)

        # For embedding we will flatten per-sample across channels (interleaved)
        flat_floats = floats.flatten()  # shape (num_samples,)

        # Step 3: normalize each floating-point sample to integer using formula:
        # A_iN = (abs(A_i) + 1) * 1_000_000 -> round to nearest integer
        signs = np.sign(flat_floats)  # will be -1.0, 0.0, or 1.0
        abs_vals = np.abs(flat_floats)
        A_iN = np.rint((abs_vals + 1.0) * self._NORMALIZE_SCALE).astype(np.int64)

        # Build payload: start_signature + message + end_signature
        start_sig, end_sig = self._signatures_for_lsb(lsb_bits)
        payload = start_sig + message_bits + end_sig
        payload_len_bits = len(payload)

        # capacity check
        required_samples = math.ceil(payload_len_bits / lsb_bits)
        if required_samples + 200 >= num_samples:
            raise ValueError(f"Insufficient capacity: need {required_samples + 200} samples but file has {num_samples}")

        # compute Irand as specified:
        Espace = num_samples - (payload_len_bits / lsb_bits) - 200
        if Espace <= 0:
            raise ValueError("Not enough free space for embedding after safety margin.")
        Irand = math.ceil(random.random() * math.floor(Espace / 2.0)) + 200
        Irand = int(Irand)

        # Embedding loop: for each sample from Irand, replace lsb_bits with payload bits
        # We'll represent A_iN in binary padded (choose 24 bits to be safe - paper suggests 24/32)
        pad_bits = 24
        payload_index = 0
        modified_A_iN = A_iN.copy()

        # convert payload to list for quicker indexing
        payload_list = list(payload)

        for i_sample in range(Irand, Irand + required_samples):
            if payload_index >= payload_len_bits:
                break

            original_val = modified_A_iN[i_sample]
            bin_str = format(int(original_val), f'0{pad_bits}b')

            # get next chunk of payload bits (lsb_bits or fewer if near end)
            chunk = ''.join(payload_list[payload_index: payload_index + lsb_bits])
            # if chunk shorter than lsb_bits (shouldn't happen because calculated required_samples),
            # pad with zeros
            if len(chunk) < lsb_bits:
                chunk = chunk.ljust(lsb_bits, '0')

            # Replace least significant lsb_bits of bin_str
            new_bin_str = bin_str[:-lsb_bits] + chunk
            new_val = int(new_bin_str, 2)
            modified_A_iN[i_sample] = new_val

            payload_index += lsb_bits

        if payload_index < payload_len_bits:
            raise RuntimeError("Embedding failed: not all payload bits were written.")

        # De-normalize: A_i = (A_iN / 1_000_000) - 1 ; reapply sign
        A_iN_float = modified_A_iN.astype(np.float64)
        de_norm = (A_iN_float / self._NORMALIZE_SCALE) - 1.0
        de_norm_signed = de_norm * signs  # reapply sign (0 sign remains 0)

        # reshape to (frames, channels)
        stego_floats = de_norm_signed.reshape((-1, channels))

        # Convert float samples [-1,1) back to PCM integer values for audio export
        pcm_ints = self._samples_float_to_int_pcm(stego_floats, sample_width)

        # pydub accepts raw bytes to create AudioSegment
        out_segment = self._int_array_to_audiosegment(pcm_ints, frame_rate, channels, sample_width)

        # export to mp3
        out_segment.export(output_mp3_path, format="mp3")
        print(f"Embedding complete. Saved stego MP3 to: {output_mp3_path}")
        print(f"Embedding metadata: lsb_bits={lsb_bits}, Irand={Irand}, payload_bits={payload_len_bits}")

    # ---------------------------
    # Extraction
    # ---------------------------
    def extract(self, input_mp3_path: str, output_text_path: str, lsb_bits: int = 1):
        """
        Extract a hidden message from input_mp3_path (stego file) assuming lsb_bits,
        and write the recovered message to output_text_path.
        """
        # load mp3 and get float samples
        floats, frame_rate, channels, sample_width = self._load_mp3_as_float_samples(input_mp3_path)
        flat_floats = floats.flatten()
        num_samples = flat_floats.shape[0]

        # Normalize into integers using same formula
        signs = np.sign(flat_floats)
        abs_vals = np.abs(flat_floats)
        A_iN = np.rint((abs_vals + 1.0) * self._NORMALIZE_SCALE).astype(np.int64)

        start_sig, end_sig = self._signatures_for_lsb(lsb_bits)
        sig_len = len(start_sig)

        pad_bits = 24  # same pad used during embedding

        # read LSBs continuously and search for start_signature
        collected_bits = []
        found_start = False
        # We'll build a rolling bit window to search for start & end signature faster
        rolling = ''

        for idx in range(0, num_samples):
            val = int(A_iN[idx])
            bin_str = format(val, f'0{pad_bits}b')
            lsb_chunk = bin_str[-lsb_bits:]  # get last lsb_bits
            rolling += lsb_chunk

            # keep rolling length reasonable (we only need to detect start_sig)
            # but keep at least sig_len bits
            if len(rolling) > sig_len + 512_000:  # safety cap (very large)
                rolling = rolling[-(sig_len + 1024):]

            if not found_start:
                # search for start signature at the end of rolling
                if rolling.endswith(start_sig):
                    found_start = True
                    # start collection AFTER the signature, so reset collected_bits
                    collected_bits = []
                    # ensure rolling after signature is empty (we want only payload)
                    rolling = ''
            else:
                # we're inside payload; append the lsb_chunk to collected_bits
                collected_bits.append(lsb_chunk)
                # to check for end signature we need to inspect the last bits of the collected stream
                # make a small string of last bits equal to sig_len
                if len(''.join(collected_bits)) >= sig_len:
                    # build last sig_len bits quickly:
                    # Note: building full string each step can be heavy; join last few elements enough to cover sig_len
                    needed_chunks = math.ceil(sig_len / lsb_bits)
                    tail = ''.join(collected_bits[-needed_chunks:])
                    # take only last sig_len bits of tail
                    tail = tail[-sig_len:]
                    if tail == end_sig:
                        # remove end signature bits from payload: drop last sig_len bits
                        full_payload_bits = ''.join(collected_bits)
                        message_bits_total = full_payload_bits[:-sig_len]  # drop end signature
                        # also remove any bits that could be part of the start signature (start signature was before collection)
                        # reconstruct message text
                        # message_bits_total length should be multiple of 8; trim trailing partial byte if necessary
                        # convert to ASCII text
                        # strip any leading bits that could be due to boundary misalignment (we assume exact)
                        message_bits = message_bits_total
                        recovered = self._bitstream_to_text(message_bits)
                        # write to file
                        with open(output_text_path, 'w', encoding='utf-8', errors='replace') as fout:
                            fout.write(recovered)
                        print(f"Extraction complete. Message saved to: {output_text_path}")
                        return
        # if we reach here, no start/end signature pair was found
        raise RuntimeError("Start or end signature not found; message may be corrupt or not present.")

# ---------------------------
# Example usage in __main__
# ---------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MP3 LSB Steganography (MP3Stego)")
    subparsers = parser.add_subparsers(dest='command', required=True)

    # embed subcommand
    e = subparsers.add_parser('embed', help='Embed a text message into an MP3')
    e.add_argument('--in-mp3', required=True, help='Input carrier MP3 path')
    e.add_argument('--in-text', required=True, help='Input text file containing secret message')
    e.add_argument('--out-mp3', required=True, help='Output stego MP3 path')
    e.add_argument('--lsb', type=int, choices=[1,2,3,4], default=1, help='Number of LSB bits to use')

    # extract subcommand
    x = subparsers.add_parser('extract', help='Extract a text message from a stego MP3')
    x.add_argument('--in-mp3', required=True, help='Input stego MP3 path')
    x.add_argument('--out-text', required=True, help='Output extracted text file')
    x.add_argument('--lsb', type=int, choices=[1,2,3,4], default=1, help='Number of LSB bits used during embedding')

    args = parser.parse_args()

    stego = MP3Stego()

    if args.command == 'embed':
        print("Embedding... (this may take a moment)")
        stego.embed(args.in_mp3, args.in_text, args.out_mp3, lsb_bits=args.lsb)
    elif args.command == 'extract':
        print("Extracting... (this may take a moment)")
        stego.extract(args.in_mp3, args.out_text, lsb_bits=args.lsb)

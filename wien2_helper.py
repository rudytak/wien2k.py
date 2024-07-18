# message box
import ctypes
import string, random, re, sys, itertools

TESSERACT_PATH = "C:/Program Files/Tesseract-OCR/tesseract.exe"
WINDOWS_LINE_ENDING = b"\r\n"
UNIX_LINE_ENDING = b"\n"
MB_SYSTEMMODAL = 0x00001000


class Constants:
    bohr_to_angstrom = 0.529177
    angstrom_to_bohr = 1.8897
    eV_to_Ry = 0.0734985857
    Ry_to_eV = 13.605703976


def lfilt(iter, func):
    return list(filter(func, iter))


def lmap(iter, func):
    return list(map(func, iter))


def flatten(iter):
    return list(itertools.chain.from_iterable(iter))


def Mbox(title, text, style, important=True):
    return ctypes.windll.user32.MessageBoxW(
        0, text, title, style + (MB_SYSTEMMODAL if important else 0)
    )


def rng_string(length):
    return "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(length)
    )


def nested_regex_replace(
    text,
    regexes,
    replaces,
    start_offset=0,
    previous_segment_len=sys.maxsize,
    depth=0,
    replace_index=0,
    keep_len=True,
):
    matches_iter = re.finditer(
        f"({regexes[depth]})",
        text[start_offset : start_offset + previous_segment_len],
        flags=re.M,
    )

    while True:
        try:
            _match = next(matches_iter)
            s = _match.start()
            e = _match.end()

            if depth == len(regexes) - 1:
                repl = replaces[replace_index]
                if type(repl) == type(float()) or type(repl) == type(int()):
                    text = "".join(
                        [
                            text[: start_offset + s],
                            f"{repl:.99f}"[0 : (e - s) if keep_len else -1],
                            text[start_offset + e :],
                        ]
                    )
                else:
                    text = "".join(
                        [
                            text[: start_offset + s],
                            str(repl)[0 : (e - s) if keep_len else -1],
                            text[start_offset + e :],
                        ]
                    )
                replace_index += 1
            else:
                text, replace_index = nested_regex_replace(
                    text,
                    regexes,
                    replaces,
                    start_offset + s,
                    e - s,
                    depth + 1,
                    replace_index,
                    keep_len,
                )
        except Exception as e:
            break

    return text, replace_index

"""Paint the three station shields on a shared 11×11 pixel grid."""
from pathlib import Path

from PIL import Image, ImageColor

ART = Path(__file__).resolve().parents[1]
SHIELD = (
    "..bbbbbbb..",
    ".bfffffffD.",
    "bfffffffffD",
    "bfffffffffD",
    "bfffffffffD",
    "bfffffffffD",
    "bfffffffffD",
    ".bfffffffD.",
    "..DfffffD..",
    "...DfffD...",
    "....DDD....",
)
RUNES = {
    "claude": ("#d97757", (
        "#..#..#",
        ".#.#.#.",
        "..###..",
        "#######",
        "..###..",
        ".#.#.#.",
        "...#...",
    )),
    # A continuous diagonal crosses over the interrupted return strand.
    "codex": ("#d7dee3", (
        ".##...##.",
        "#..#.#..#",
        "#..#....#",
        "#...#...#",
        "#....#..#",
        ".#.#.#.#.",
        "..#...#..",
    )),
    "other": ("#58d39e", ("..#..", ".#.#.", "#...#", ".#.#.", "..#..")),
}

strip = Image.new("RGB", (41, 15), "#101215")
for index, (provider, (ink, rune)) in enumerate(RUNES.items()):
    image = Image.new("RGBA", (11, 11))
    palette = {"b": "#8594a6", "f": "#20232d", "D": "#4f5e71", "#": ink}
    inset = (11 - len(rune[0])) // 2
    for rows, left, top in ((SHIELD, 0, 0), (rune, inset, (11 - len(rune)) // 2)):
        for y, row in enumerate(rows, top):
            for x, pixel in enumerate(row, left):
                if pixel in palette:
                    image.putpixel((x, y), ImageColor.getcolor(palette[pixel], "RGBA"))
    image.save(ART / f"sign-{provider}.png")
    strip.paste(image, (2 + index * 13, 2), image)

strip.resize((410, 150), Image.Resampling.NEAREST).save(ART / "src/_provider_signs_x10.png")

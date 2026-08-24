"""Generate a grayscale elevation bitmap from layered Perlin-style noise.

Example:
    python -m tools.create_elevation_bitmap terrain.png --width 512 --height 512

"""

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PySide6.QtGui import QImage


def _fade(values):
    """Smooth interpolation curve used by Perlin noise."""
    return values * values * values * (values * (values * 6 - 15) + 10)


def _interpolate(left, right, amount):
    return left + amount * (right - left)


@dataclass
class DotGradient:
    fraction_x: np.ndarray
    fraction_y: np.ndarray
    gradients_x: np.ndarray
    gradients_y: np.ndarray
    cell_x: np.ndarray
    cell_y: np.ndarray

    def calculate(self, offset_x: int, offset_y: int) -> np.ndarray:
        gradient_x = self.gradients_x[
            self.cell_y + offset_y,
            self.cell_x + offset_x,
        ]
        gradient_y = self.gradients_y[
            self.cell_y + offset_y,
            self.cell_x + offset_x,
        ]
        distance_x = self.fraction_x - offset_x
        distance_y = self.fraction_y - offset_y
        return gradient_x * distance_x + gradient_y * distance_y


def generate_perlin_noise(
    width: int,
    height: int,
    grid_size: int = 8,
    octaves: int = 4,
    persistence: float = 0.5,
    seed: int | None = None,
) -> np.ndarray:
    """Return normalized layered Perlin noise as a float array in ``[0, 1]``."""
    if width < 1 or height < 1:
        raise ValueError("width and height must be positive")
    if grid_size < 1:
        raise ValueError("grid_size must be positive")
    if octaves < 1:
        raise ValueError("octaves must be positive")
    if not 0 < persistence <= 1:
        raise ValueError("persistence must be greater than 0 and at most 1")

    rng = np.random.default_rng(seed)
    coordinates_y, coordinates_x = np.mgrid[0:height, 0:width]
    normalized_x = coordinates_x / max(width - 1, 1)
    normalized_y = coordinates_y / max(height - 1, 1)

    result = np.zeros((height, width), dtype=float)
    amplitude = 1.0
    amplitude_total = 0.0

    for octave in range(octaves):
        cells_x = grid_size * (2**octave)
        cells_y = max(1, round(cells_x * height / width))
        sample_x = normalized_x * cells_x
        sample_y = normalized_y * cells_y
        cell_x = np.minimum(np.floor(sample_x).astype(int), cells_x - 1)
        cell_y = np.minimum(np.floor(sample_y).astype(int), cells_y - 1)
        fraction_x = sample_x - cell_x
        fraction_y = sample_y - cell_y

        angles = rng.uniform(
            0,
            2 * np.pi,
            size=(cells_y + 1, cells_x + 1),
        )
        gradients_x = np.cos(angles)
        gradients_y = np.sin(angles)

        dot_gradient = DotGradient(
            fraction_x=fraction_x,
            fraction_y=fraction_y,
            gradients_x=gradients_x,
            gradients_y=gradients_y,
            cell_x=cell_x,
            cell_y=cell_y,
        )

        top = _interpolate(
            dot_gradient.calculate(0, 0),
            dot_gradient.calculate(1, 0),
            _fade(fraction_x),
        )
        bottom = _interpolate(
            dot_gradient.calculate(0, 1),
            dot_gradient.calculate(1, 1),
            _fade(fraction_x),
        )
        result += amplitude * _interpolate(
            top,
            bottom,
            _fade(fraction_y),
        )
        amplitude_total += amplitude
        amplitude *= persistence

    result /= amplitude_total
    result -= result.min()
    maximum = result.max()
    if maximum > 0:
        result /= maximum
    return result


def save_elevation_bitmap(
    output_path: str | Path,
    width: int = 100,
    height: int = 100,
    grid_size: int = 8,
    octaves: int = 4,
    persistence: float = 0.5,
    seed: int | None = None,
) -> Path:
    """Generate and save an 8-bit grayscale elevation bitmap."""
    noise = generate_perlin_noise(
        width=width,
        height=height,
        grid_size=grid_size,
        octaves=octaves,
        persistence=persistence,
        seed=seed,
    )
    pixels = np.rint(noise * 255).astype(np.uint8)
    image = QImage(
        pixels.data,
        width,
        height,
        pixels.strides[0],
        QImage.Format.Format_Grayscale8,
    ).copy()
    output = Path(output_path)
    if not output.suffix:
        output = output.with_suffix(".png")
    output.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(output)):
        raise OSError(f"Unable to save elevation bitmap: {output}")
    return output


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Create a grayscale elevation bitmap from layered Perlin noise."
    )
    parser.add_argument(
        "output", type=Path, help="Output image path, such as terrain.png"
    )
    parser.add_argument("--width", type=int, default=100)
    parser.add_argument("--height", type=int, default=100)
    parser.add_argument(
        "--grid-size",
        type=int,
        default=8,
        help="Number of broad noise cells across the image",
    )
    parser.add_argument("--octaves", type=int, default=4)
    parser.add_argument("--persistence", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=None)
    return parser.parse_args()


def main():
    args = _parse_args()
    output = save_elevation_bitmap(
        output_path=args.output,
        width=args.width,
        height=args.height,
        grid_size=args.grid_size,
        octaves=args.octaves,
        persistence=args.persistence,
        seed=args.seed,
    )
    print(f"Saved elevation bitmap to {output}")


if __name__ == "__main__":
    main()

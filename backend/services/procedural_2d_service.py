"""
Procedural 2D Image Generation Service.
Generates centered 2D object images from text prompts using CPU-only rendering.
No ML/GPU required - uses heuristics and Pillow for fast, cheap generation.
"""

import os
import uuid
import re
from datetime import datetime
from typing import Dict, Tuple, Optional
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import colorsys

from config import IMAGES_DIR


class Procedural2DService:
    """
    Service for generating 2D reference images using procedural methods.
    Parses prompts to extract shape, color, and size cues, then renders
    a centered object using Pillow.
    """

    def __init__(self):
        """Initialize the procedural 2D service."""
        self.shape_keywords = {
            # Triangle shapes
            "triangle": {"shape": "triangle", "aspect": "square"},
            "pyramid": {"shape": "triangle", "aspect": "square"},
            "arrow": {"shape": "arrow", "aspect": "tall"},
            "arrowhead": {"shape": "triangle", "aspect": "square"},
            
            # Star shapes
            "star": {"shape": "star", "aspect": "square"},
            "sparkle": {"shape": "star", "aspect": "square"},
            
            # Diamond shapes
            "diamond": {"shape": "diamond", "aspect": "square"},
            "rhombus": {"shape": "diamond", "aspect": "square"},
            "crystal": {"shape": "diamond", "aspect": "tall"},
            
            # Heart shape
            "heart": {"shape": "heart", "aspect": "square"},
            "love": {"shape": "heart", "aspect": "square"},
            
            # Wheel with spokes
            "wheel": {"shape": "wheel", "aspect": "square"},
            "tire": {"shape": "wheel", "aspect": "square"},
            "gear": {"shape": "gear", "aspect": "square"},
            "cog": {"shape": "gear", "aspect": "square"},
            
            # Hexagon
            "hexagon": {"shape": "hexagon", "aspect": "square"},
            "hex": {"shape": "hexagon", "aspect": "square"},
            "honeycomb": {"shape": "hexagon", "aspect": "square"},
            
            # Pentagon
            "pentagon": {"shape": "pentagon", "aspect": "square"},
            
            # Cross/Plus
            "cross": {"shape": "cross", "aspect": "square"},
            "plus": {"shape": "cross", "aspect": "square"},
            "health": {"shape": "cross", "aspect": "square"},
            
            # Long/tall objects
            "sword": {"shape": "sword", "aspect": "tall"},
            "spear": {"shape": "tall", "aspect": "tall"},
            "wand": {"shape": "tall", "aspect": "tall"},
            "staff": {"shape": "tall", "aspect": "tall"},
            "knife": {"shape": "sword", "aspect": "tall"},
            "blade": {"shape": "sword", "aspect": "tall"},
            "rod": {"shape": "tall", "aspect": "tall"},
            "pole": {"shape": "tall", "aspect": "tall"},
            "tree": {"shape": "tree", "aspect": "tall"},
            "tower": {"shape": "tall", "aspect": "tall"},
            
            # Box/square objects
            "crate": {"shape": "box", "aspect": "square"},
            "box": {"shape": "box", "aspect": "square"},
            "cube": {"shape": "box", "aspect": "square"},
            "square": {"shape": "box", "aspect": "square"},
            "shield": {"shape": "shield", "aspect": "tall"},
            "chest": {"shape": "box", "aspect": "square"},
            "container": {"shape": "box", "aspect": "square"},
            "block": {"shape": "box", "aspect": "square"},
            "door": {"shape": "box", "aspect": "tall"},
            "window": {"shape": "box", "aspect": "square"},
            "rectangle": {"shape": "box", "aspect": "wide"},
            
            # Round objects
            "coin": {"shape": "round", "aspect": "square"},
            "orb": {"shape": "round", "aspect": "square"},
            "ball": {"shape": "round", "aspect": "square"},
            "sphere": {"shape": "round", "aspect": "square"},
            "pearl": {"shape": "round", "aspect": "square"},
            "ring": {"shape": "ring", "aspect": "square"},
            "circle": {"shape": "round", "aspect": "square"},
            "button": {"shape": "round", "aspect": "square"},
            "eye": {"shape": "round", "aspect": "square"},
            "sun": {"shape": "sun", "aspect": "square"},
            "moon": {"shape": "crescent", "aspect": "square"},
            
            # Gem shapes
            "gem": {"shape": "gem", "aspect": "square"},
            "jewel": {"shape": "gem", "aspect": "square"},
            "ruby": {"shape": "gem", "aspect": "square"},
            "emerald": {"shape": "gem", "aspect": "square"},
            "sapphire": {"shape": "gem", "aspect": "square"},
            
            # Bottle-shaped objects
            "potion": {"shape": "bottle", "aspect": "tall"},
            "bottle": {"shape": "bottle", "aspect": "tall"},
            "flask": {"shape": "bottle", "aspect": "tall"},
            "vial": {"shape": "bottle", "aspect": "tall"},
            
            # Wide objects
            "plate": {"shape": "wide", "aspect": "wide"},
            "disk": {"shape": "round", "aspect": "square"},
            "table": {"shape": "wide", "aspect": "wide"},
            "platform": {"shape": "wide", "aspect": "wide"},
            "car": {"shape": "wide", "aspect": "wide"},
            "vehicle": {"shape": "wide", "aspect": "wide"},
        }

        self.color_map = {
            "red": (220, 50, 50),
            "blue": (50, 100, 220),
            "green": (50, 180, 50),
            "yellow": (220, 180, 50),
            "purple": (150, 50, 220),
            "orange": (255, 140, 50),
            "pink": (255, 150, 200),
            "brown": (150, 100, 50),
            "black": (40, 40, 40),
            "white": (240, 240, 240),
            "gray": (150, 150, 150),
            "grey": (150, 150, 150),
            "silver": (190, 190, 200),
            "gold": (255, 200, 50),
            "golden": (255, 200, 50),
            "cyan": (50, 200, 200),
            "magenta": (220, 50, 150),
        }

        self.size_keywords = {
            "tiny": 0.4,
            "small": 0.5,
            "compact": 0.5,
            "medium": 0.6,
            "large": 0.7,
            "big": 0.7,
            "huge": 0.8,
            "massive": 0.85,
            "giant": 0.85,
        }

        self.quality_keywords = {
            "common": {"colors": [(150, 150, 150), (100, 100, 120)], "glow": False},
            "basic": {"colors": [(150, 150, 150), (100, 100, 120)], "glow": False},
            "uncommon": {"colors": [(50, 150, 50), (30, 100, 30)], "glow": False},
            "rare": {"colors": [(50, 100, 220), (30, 70, 150)], "glow": True},
            "epic": {"colors": [(150, 50, 220), (100, 30, 150)], "glow": True},
            "legendary": {"colors": [(255, 200, 50), (200, 150, 30)], "glow": True},
            "mythic": {"colors": [(255, 100, 50), (200, 70, 30)], "glow": True},
        }

    def parse_prompt(self, prompt: str) -> Dict:
        """
        Parse a text prompt to extract shape, color, and size parameters.
        
        Args:
            prompt: User's text description
            
        Returns:
            Dictionary with parsed parameters for rendering
        """
        prompt_lower = prompt.lower()
        
        # Default parameters
        params = {
            "shape": "blob",
            "aspect": "square",
            "primary_color": (120, 120, 140),
            "secondary_color": (80, 80, 100),
            "size_factor": 0.6,
            "border": True,
            "glow": False,
            "gradient": True,
        }

        # Extract shape from keywords
        for keyword, shape_info in self.shape_keywords.items():
            if keyword in prompt_lower:
                params["shape"] = shape_info["shape"]
                params["aspect"] = shape_info["aspect"]
                break

        # Extract colors
        found_colors = []
        for color_name, color_value in self.color_map.items():
            if color_name in prompt_lower:
                found_colors.append(color_value)
                
        if found_colors:
            params["primary_color"] = found_colors[0]
            if len(found_colors) > 1:
                params["secondary_color"] = found_colors[1]
            else:
                # Generate a darker version of primary for secondary
                params["secondary_color"] = tuple(int(c * 0.7) for c in found_colors[0])

        # Extract size
        for size_word, size_factor in self.size_keywords.items():
            if size_word in prompt_lower:
                params["size_factor"] = size_factor
                break

        # Extract quality/rarity for special effects
        for quality_word, quality_info in self.quality_keywords.items():
            if quality_word in prompt_lower:
                params["primary_color"] = quality_info["colors"][0]
                params["secondary_color"] = quality_info["colors"][1]
                params["glow"] = quality_info["glow"]
                break

        # Special effects detection
        if any(word in prompt_lower for word in ["glowing", "glow", "shine", "shimmer"]):
            params["glow"] = True
            
        if any(word in prompt_lower for word in ["metallic", "metal", "chrome"]):
            params["gradient"] = True
            params["border"] = True

        return params

    def _get_polygon_points(self, shape: str, center: int, radius: int) -> list:
        """Generate polygon points for various shapes."""
        import math
        points = []
        
        if shape == "triangle":
            # Equilateral triangle pointing up
            for i in range(3):
                angle = math.radians(90 + i * 120)
                x = center + radius * math.cos(angle)
                y = center - radius * math.sin(angle)
                points.append((x, y))
                
        elif shape == "diamond":
            # Diamond/rhombus
            points = [
                (center, center - radius),      # top
                (center + radius, center),      # right
                (center, center + radius),      # bottom
                (center - radius, center),      # left
            ]
            
        elif shape == "star":
            # 5-pointed star
            outer_radius = radius
            inner_radius = radius * 0.4
            for i in range(10):
                angle = math.radians(90 + i * 36)
                r = outer_radius if i % 2 == 0 else inner_radius
                x = center + r * math.cos(angle)
                y = center - r * math.sin(angle)
                points.append((x, y))
                
        elif shape == "hexagon":
            for i in range(6):
                angle = math.radians(30 + i * 60)
                x = center + radius * math.cos(angle)
                y = center - radius * math.sin(angle)
                points.append((x, y))
                
        elif shape == "pentagon":
            for i in range(5):
                angle = math.radians(90 + i * 72)
                x = center + radius * math.cos(angle)
                y = center - radius * math.sin(angle)
                points.append((x, y))
                
        elif shape == "arrow":
            # Arrow pointing up
            w = radius * 0.6
            h = radius
            points = [
                (center, center - h),           # tip
                (center + w, center),           # right wing
                (center + w * 0.3, center),     # right notch
                (center + w * 0.3, center + h), # right base
                (center - w * 0.3, center + h), # left base
                (center - w * 0.3, center),     # left notch
                (center - w, center),           # left wing
            ]
            
        elif shape == "heart":
            # Heart shape using bezier approximation
            scale = radius / 100
            heart_points = [
                (0, -30), (50, -80), (100, -30), (100, 20),
                (50, 80), (0, 100), (-50, 80), (-100, 20),
                (-100, -30), (-50, -80), (0, -30)
            ]
            points = [(center + p[0] * scale, center + p[1] * scale) for p in heart_points]
            
        elif shape == "gem":
            # Gem/jewel shape (octagon-ish with flat top)
            w = radius
            h = radius * 1.2
            points = [
                (center - w * 0.4, center - h * 0.8),  # top left
                (center + w * 0.4, center - h * 0.8),  # top right
                (center + w, center - h * 0.2),        # upper right
                (center + w, center + h * 0.2),        # lower right
                (center + w * 0.4, center + h * 0.8),  # bottom right
                (center - w * 0.4, center + h * 0.8),  # bottom left
                (center - w, center + h * 0.2),        # lower left
                (center - w, center - h * 0.2),        # upper left
            ]
            
        return points

    def render_2d_proxy(self, params: Dict, size: int = 512) -> bytes:
        """
        Render a 2D proxy object based on parsed parameters.
        
        Args:
            params: Rendering parameters from parse_prompt
            size: Output image size (square)
            
        Returns:
            PNG image as bytes
        """
        import math
        import io
        
        # Create image with transparent background
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        center = size // 2
        size_factor = params["size_factor"]
        shape = params["shape"]
        
        # Calculate base dimensions
        if params["aspect"] == "tall":
            width = int(size * size_factor * 0.4)
            height = int(size * size_factor * 0.8)
        elif params["aspect"] == "wide":
            width = int(size * size_factor * 0.8)
            height = int(size * size_factor * 0.4)
        else:  # square
            width = height = int(size * size_factor * 0.6)
        
        radius = min(width, height) // 2
        primary = params["primary_color"]
        secondary = params["secondary_color"]
        border_width = max(3, size // 100)
        shadow_offset = max(6, size // 50)
        
        # Helper to darken color
        def darken(color, factor=0.6):
            return tuple(int(c * factor) for c in color)
        
        def lighten(color, factor=1.3):
            return tuple(min(255, int(c * factor)) for c in color)

        # Draw shadow first
        shadow_color = (0, 0, 0, 50)
        
        # Draw main shape based on type
        if shape == "triangle":
            points = self._get_polygon_points("triangle", center, radius)
            shadow_points = [(p[0] + shadow_offset, p[1] + shadow_offset) for p in points]
            draw.polygon(shadow_points, fill=shadow_color)
            draw.polygon(points, fill=primary, outline=darken(secondary), width=border_width)
            
        elif shape == "diamond":
            points = self._get_polygon_points("diamond", center, radius)
            shadow_points = [(p[0] + shadow_offset, p[1] + shadow_offset) for p in points]
            draw.polygon(shadow_points, fill=shadow_color)
            draw.polygon(points, fill=primary, outline=darken(secondary), width=border_width)
            # Add shine
            shine_points = [
                (center, center - radius + 10),
                (center + radius * 0.3, center),
                (center, center + radius * 0.3),
                (center - radius * 0.3, center),
            ]
            draw.polygon(shine_points, fill=lighten(primary))
            
        elif shape == "star":
            points = self._get_polygon_points("star", center, radius)
            shadow_points = [(p[0] + shadow_offset, p[1] + shadow_offset) for p in points]
            draw.polygon(shadow_points, fill=shadow_color)
            draw.polygon(points, fill=primary, outline=darken(secondary), width=border_width)
            
        elif shape == "heart":
            points = self._get_polygon_points("heart", center, radius)
            shadow_points = [(p[0] + shadow_offset, p[1] + shadow_offset) for p in points]
            draw.polygon(shadow_points, fill=shadow_color)
            draw.polygon(points, fill=primary, outline=darken(secondary), width=border_width)
            
        elif shape == "hexagon":
            points = self._get_polygon_points("hexagon", center, radius)
            shadow_points = [(p[0] + shadow_offset, p[1] + shadow_offset) for p in points]
            draw.polygon(shadow_points, fill=shadow_color)
            draw.polygon(points, fill=primary, outline=darken(secondary), width=border_width)
            
        elif shape == "pentagon":
            points = self._get_polygon_points("pentagon", center, radius)
            shadow_points = [(p[0] + shadow_offset, p[1] + shadow_offset) for p in points]
            draw.polygon(shadow_points, fill=shadow_color)
            draw.polygon(points, fill=primary, outline=darken(secondary), width=border_width)
            
        elif shape == "arrow":
            points = self._get_polygon_points("arrow", center, radius)
            shadow_points = [(p[0] + shadow_offset, p[1] + shadow_offset) for p in points]
            draw.polygon(shadow_points, fill=shadow_color)
            draw.polygon(points, fill=primary, outline=darken(secondary), width=border_width)
            
        elif shape == "gem":
            points = self._get_polygon_points("gem", center, radius)
            shadow_points = [(p[0] + shadow_offset, p[1] + shadow_offset) for p in points]
            draw.polygon(shadow_points, fill=shadow_color)
            draw.polygon(points, fill=primary, outline=darken(secondary), width=border_width)
            # Add facet shine
            draw.line([(center, center - radius * 0.6), (center + radius * 0.5, center)], 
                     fill=lighten(primary), width=3)
            draw.line([(center, center - radius * 0.6), (center - radius * 0.5, center)], 
                     fill=lighten(primary), width=3)
            
        elif shape == "wheel":
            # Wheel with spokes
            outer_r = radius
            inner_r = radius * 0.3
            hub_r = radius * 0.15
            
            # Shadow
            draw.ellipse([center - outer_r + shadow_offset, center - outer_r + shadow_offset,
                         center + outer_r + shadow_offset, center + outer_r + shadow_offset], 
                        fill=shadow_color)
            
            # Outer tire
            draw.ellipse([center - outer_r, center - outer_r, center + outer_r, center + outer_r], 
                        fill=darken(primary, 0.4), outline=darken(secondary), width=border_width)
            
            # Inner wheel
            draw.ellipse([center - inner_r * 2.5, center - inner_r * 2.5, 
                         center + inner_r * 2.5, center + inner_r * 2.5], 
                        fill=primary)
            
            # Spokes
            num_spokes = 6
            for i in range(num_spokes):
                angle = math.radians(i * (360 / num_spokes))
                x1 = center + hub_r * math.cos(angle)
                y1 = center + hub_r * math.sin(angle)
                x2 = center + (outer_r - 15) * math.cos(angle)
                y2 = center + (outer_r - 15) * math.sin(angle)
                draw.line([(x1, y1), (x2, y2)], fill=darken(primary, 0.7), width=max(4, size // 60))
            
            # Hub
            draw.ellipse([center - hub_r, center - hub_r, center + hub_r, center + hub_r], 
                        fill=lighten(primary), outline=darken(secondary), width=2)
            
        elif shape == "gear":
            # Gear with teeth
            outer_r = radius
            inner_r = radius * 0.7
            hub_r = radius * 0.25
            num_teeth = 8
            
            # Shadow
            draw.ellipse([center - outer_r + shadow_offset, center - outer_r + shadow_offset,
                         center + outer_r + shadow_offset, center + outer_r + shadow_offset], 
                        fill=shadow_color)
            
            # Draw gear teeth
            tooth_points = []
            for i in range(num_teeth * 2):
                angle = math.radians(i * (360 / (num_teeth * 2)))
                r = outer_r if i % 2 == 0 else inner_r
                x = center + r * math.cos(angle)
                y = center + r * math.sin(angle)
                tooth_points.append((x, y))
            
            draw.polygon(tooth_points, fill=primary, outline=darken(secondary), width=border_width)
            
            # Hub hole
            draw.ellipse([center - hub_r, center - hub_r, center + hub_r, center + hub_r], 
                        fill=darken(primary, 0.3), outline=darken(secondary), width=2)
            
        elif shape == "cross":
            # Plus/cross shape
            arm_width = radius * 0.4
            arm_length = radius
            
            # Shadow
            draw.rectangle([center - arm_width + shadow_offset, center - arm_length + shadow_offset,
                           center + arm_width + shadow_offset, center + arm_length + shadow_offset], 
                          fill=shadow_color)
            draw.rectangle([center - arm_length + shadow_offset, center - arm_width + shadow_offset,
                           center + arm_length + shadow_offset, center + arm_width + shadow_offset], 
                          fill=shadow_color)
            
            # Vertical arm
            draw.rectangle([center - arm_width, center - arm_length,
                           center + arm_width, center + arm_length], 
                          fill=primary, outline=darken(secondary), width=border_width)
            # Horizontal arm
            draw.rectangle([center - arm_length, center - arm_width,
                           center + arm_length, center + arm_width], 
                          fill=primary, outline=darken(secondary), width=border_width)
            
        elif shape == "ring":
            # Ring/donut shape
            outer_r = radius
            inner_r = radius * 0.5
            
            # Shadow
            draw.ellipse([center - outer_r + shadow_offset, center - outer_r + shadow_offset,
                         center + outer_r + shadow_offset, center + outer_r + shadow_offset], 
                        fill=shadow_color)
            
            # Outer circle
            draw.ellipse([center - outer_r, center - outer_r, center + outer_r, center + outer_r], 
                        fill=primary, outline=darken(secondary), width=border_width)
            # Inner hole (transparent)
            draw.ellipse([center - inner_r, center - inner_r, center + inner_r, center + inner_r], 
                        fill=(0, 0, 0, 0))
            
        elif shape == "sun":
            # Sun with rays
            body_r = radius * 0.5
            ray_length = radius * 0.4
            num_rays = 12
            
            # Shadow
            draw.ellipse([center - body_r + shadow_offset, center - body_r + shadow_offset,
                         center + body_r + shadow_offset, center + body_r + shadow_offset], 
                        fill=shadow_color)
            
            # Rays
            for i in range(num_rays):
                angle = math.radians(i * (360 / num_rays))
                x1 = center + body_r * math.cos(angle)
                y1 = center + body_r * math.sin(angle)
                x2 = center + (body_r + ray_length) * math.cos(angle)
                y2 = center + (body_r + ray_length) * math.sin(angle)
                draw.line([(x1, y1), (x2, y2)], fill=primary, width=max(6, size // 50))
            
            # Sun body
            draw.ellipse([center - body_r, center - body_r, center + body_r, center + body_r], 
                        fill=primary, outline=darken(secondary), width=border_width)
            
        elif shape == "crescent":
            # Crescent moon
            # Shadow
            draw.ellipse([center - radius + shadow_offset, center - radius + shadow_offset,
                         center + radius + shadow_offset, center + radius + shadow_offset], 
                        fill=shadow_color)
            
            # Main moon circle
            draw.ellipse([center - radius, center - radius, center + radius, center + radius], 
                        fill=primary)
            # Cut out circle to make crescent
            cut_offset = radius * 0.5
            draw.ellipse([center - radius + cut_offset, center - radius,
                         center + radius + cut_offset, center + radius], 
                        fill=(0, 0, 0, 0))
            
        elif shape == "sword":
            # Sword shape
            blade_w = width * 0.15
            blade_h = height * 0.7
            guard_w = width * 0.5
            guard_h = height * 0.08
            handle_w = width * 0.1
            handle_h = height * 0.2
            
            # Shadow offset
            so = shadow_offset
            
            # Blade shadow
            blade_points = [
                (center, center - blade_h // 2),  # tip
                (center + blade_w, center + blade_h // 2 - guard_h),
                (center - blade_w, center + blade_h // 2 - guard_h),
            ]
            shadow_blade = [(p[0] + so, p[1] + so) for p in blade_points]
            draw.polygon(shadow_blade, fill=shadow_color)
            
            # Blade
            draw.polygon(blade_points, fill=lighten(primary), outline=darken(secondary), width=2)
            
            # Guard
            guard_y = center + blade_h // 2 - guard_h
            draw.rectangle([center - guard_w, guard_y, center + guard_w, guard_y + guard_h], 
                          fill=darken(primary, 0.8), outline=darken(secondary), width=2)
            
            # Handle
            handle_y = guard_y + guard_h
            draw.rectangle([center - handle_w, handle_y, center + handle_w, handle_y + handle_h], 
                          fill=darken(primary, 0.5), outline=darken(secondary), width=2)
            
            # Pommel
            pommel_r = handle_w * 1.2
            pommel_y = handle_y + handle_h + pommel_r
            draw.ellipse([center - pommel_r, pommel_y - pommel_r, 
                         center + pommel_r, pommel_y + pommel_r], 
                        fill=primary, outline=darken(secondary), width=2)
            
        elif shape == "shield":
            # Shield shape
            points = [
                (center, center - height // 2),           # top center
                (center + width // 2, center - height // 3),  # top right
                (center + width // 2, center + height // 4),  # mid right
                (center, center + height // 2),           # bottom point
                (center - width // 2, center + height // 4),  # mid left
                (center - width // 2, center - height // 3),  # top left
            ]
            shadow_points = [(p[0] + shadow_offset, p[1] + shadow_offset) for p in points]
            draw.polygon(shadow_points, fill=shadow_color)
            draw.polygon(points, fill=primary, outline=darken(secondary), width=border_width)
            
            # Shield emblem (inner shape)
            inner_scale = 0.6
            inner_points = [(center + (p[0] - center) * inner_scale, 
                           center + (p[1] - center) * inner_scale) for p in points]
            draw.polygon(inner_points, fill=lighten(primary), outline=darken(secondary), width=2)
            
        elif shape == "tree":
            # Simple tree
            trunk_w = width * 0.2
            trunk_h = height * 0.4
            crown_r = width * 0.5
            
            # Shadow
            draw.ellipse([center - crown_r + shadow_offset, center - height // 2 + shadow_offset,
                         center + crown_r + shadow_offset, center + shadow_offset], 
                        fill=shadow_color)
            
            # Trunk
            trunk_top = center
            trunk_bottom = center + height // 2
            draw.rectangle([center - trunk_w, trunk_top, center + trunk_w, trunk_bottom], 
                          fill=(139, 90, 43))  # brown
            
            # Crown (foliage)
            draw.ellipse([center - crown_r, center - height // 2, center + crown_r, center], 
                        fill=primary, outline=darken(primary), width=border_width)
            
        elif shape == "bottle":
            # Bottle shape
            body_width = width
            body_height = int(height * 0.6)
            neck_width = width * 0.4
            neck_height = int(height * 0.3)
            
            body_top = center
            body_bottom = center + body_height // 2
            neck_top = center - body_height // 2 - neck_height
            neck_bottom = center - body_height // 2
            
            # Shadow
            draw.rounded_rectangle([center - body_width // 2 + shadow_offset, body_top - body_height // 2 + shadow_offset,
                                   center + body_width // 2 + shadow_offset, body_bottom + shadow_offset], 
                                  radius=15, fill=shadow_color)
            
            # Body
            draw.rounded_rectangle([center - body_width // 2, body_top - body_height // 2,
                                   center + body_width // 2, body_bottom], 
                                  radius=15, fill=primary, outline=darken(secondary), width=border_width)
            
            # Neck
            draw.rectangle([center - neck_width // 2, neck_top, center + neck_width // 2, neck_bottom], 
                          fill=primary, outline=darken(secondary), width=border_width)
            
            # Cork/cap
            cap_h = neck_height * 0.3
            draw.rectangle([center - neck_width // 2 - 2, neck_top - cap_h,
                           center + neck_width // 2 + 2, neck_top], 
                          fill=darken(primary, 0.5))
            
        elif shape == "round":
            # Simple circle
            draw.ellipse([center - radius + shadow_offset, center - radius + shadow_offset,
                         center + radius + shadow_offset, center + radius + shadow_offset], 
                        fill=shadow_color)
            draw.ellipse([center - radius, center - radius, center + radius, center + radius], 
                        fill=primary, outline=darken(secondary), width=border_width)
            # Highlight
            highlight_r = radius * 0.3
            draw.ellipse([center - radius * 0.4, center - radius * 0.4,
                         center - radius * 0.4 + highlight_r, center - radius * 0.4 + highlight_r], 
                        fill=lighten(primary))
            
        else:  # box or default blob
            # Rounded rectangle
            draw.rounded_rectangle([center - width // 2 + shadow_offset, center - height // 2 + shadow_offset,
                                   center + width // 2 + shadow_offset, center + height // 2 + shadow_offset], 
                                  radius=max(10, size // 40), fill=shadow_color)
            draw.rounded_rectangle([center - width // 2, center - height // 2,
                                   center + width // 2, center + height // 2], 
                                  radius=max(10, size // 40), fill=primary, 
                                  outline=darken(secondary), width=border_width)

        # Add glow effect if enabled
        if params["glow"]:
            # Create a new layer for glow
            glow_image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_image)
            
            for i in range(5, 0, -1):
                glow_r = radius + i * 10
                glow_alpha = 30 - i * 5
                glow_color = (*primary, glow_alpha)
                glow_draw.ellipse([center - glow_r, center - glow_r, 
                                  center + glow_r, center + glow_r], 
                                 fill=glow_color)
            
            # Composite glow under main image
            result = Image.alpha_composite(glow_image, image)
            image = result

        # Convert to bytes
        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()

    async def generate_2d_image(
        self, 
        prompt: str, 
        refinement_notes: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Generate a 2D reference image using procedural methods.
        
        Args:
            prompt: Text description of the desired object
            refinement_notes: Optional refinement instructions (affects rendering)
            
        Returns:
            Tuple of (local_file_path, image_url, filename)
        """
        # Parse the prompt to get rendering parameters
        params = self.parse_prompt(prompt)
        
        # Apply refinement notes if provided
        if refinement_notes:
            refinement_params = self.parse_prompt(refinement_notes)
            # Merge refinement parameters, with refinement taking precedence
            params.update(refinement_params)
        
        # Render the image
        image_bytes = self.render_2d_proxy(params, size=512)
        
        # Save to file
        filename = f"proc_{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        local_path = IMAGES_DIR / filename
        
        with open(local_path, "wb") as f:
            f.write(image_bytes)
        
        # Return local path, dummy URL (since we're not using external API), and filename
        return str(local_path), f"/storage/images/{filename}", filename


# Singleton instance
_procedural_service: Optional[Procedural2DService] = None


def get_procedural_2d_service() -> Procedural2DService:
    """
    Get or create the procedural 2D service singleton.
    
    Returns:
        Procedural2DService instance
    """
    global _procedural_service
    if _procedural_service is None:
        _procedural_service = Procedural2DService()
    return _procedural_service

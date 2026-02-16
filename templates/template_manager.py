"""
Template Manager

Manages genre-specific project templates and production presets.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class TrackTemplate:
    """Template for a single track"""
    name: str
    type: str  # audio, midi, return
    color: Optional[int] = None
    devices: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectTemplate:
    """Template for a project/session"""
    name: str
    genre: str
    description: str
    tempo: float
    time_signature: tuple = (4, 4)
    tracks: List[TrackTemplate] = field(default_factory=list)
    return_tracks: List[TrackTemplate] = field(default_factory=list)
    master_devices: List[str] = field(default_factory=list)
    tips: List[str] = field(default_factory=list)


class TemplateManager:
    """
    Manages project templates
    
    Features:
    - Genre-specific templates
    - Quick session setup
    - Production tips per genre
    """
    
    def __init__(self):
        self.templates: Dict[str, ProjectTemplate] = {}
        self._load_builtin_templates()
    
    def _load_builtin_templates(self):
        """Load built-in genre templates"""
        
        # Trap Template
        self.templates["trap"] = ProjectTemplate(
            name="Trap Beat",
            genre="trap",
            description="Modern trap production template with 808 bass focus",
            tempo=140,
            time_signature=(4, 4),
            tracks=[
                TrackTemplate(
                    name="Kick",
                    type="midi",
                    devices=["Drum Rack"],
                    settings={"role": "kick_808"}
                ),
                TrackTemplate(
                    name="808",
                    type="midi", 
                    devices=["Operator"],
                    settings={"sub_bass": True, "glide": True}
                ),
                TrackTemplate(
                    name="Snare",
                    type="midi",
                    devices=["Drum Rack", "Reverb"],
                    settings={"reverb_short": True}
                ),
                TrackTemplate(
                    name="Hi-Hats",
                    type="midi",
                    devices=["Drum Rack"],
                    settings={"velocity_variation": True}
                ),
                TrackTemplate(
                    name="Percs",
                    type="midi",
                    devices=["Drum Rack"],
                    settings={}
                ),
                TrackTemplate(
                    name="Melody",
                    type="midi",
                    devices=["Wavetable"],
                    settings={"dark": True}
                ),
                TrackTemplate(
                    name="Chords",
                    type="midi",
                    devices=["Wavetable"],
                    settings={}
                ),
                TrackTemplate(
                    name="FX",
                    type="audio",
                    devices=[],
                    settings={}
                ),
            ],
            return_tracks=[
                TrackTemplate(
                    name="Reverb",
                    type="return",
                    devices=["Reverb"],
                    settings={"decay": 1.5}
                ),
                TrackTemplate(
                    name="Delay",
                    type="return",
                    devices=["Simple Delay"],
                    settings={"sync": True}
                ),
            ],
            master_devices=["EQ Eight", "Glue Compressor", "Limiter"],
            tips=[
                "808 should dominate the low end",
                "Use triplet hi-hat patterns",
                "Layer snares for impact",
                "Add short reverb to snare",
                "Use pitch slides on 808"
            ]
        )
        
        # Hip Hop Template
        self.templates["hip_hop"] = ProjectTemplate(
            name="Hip Hop Beat",
            genre="hip_hop",
            description="Classic hip hop boom bap style template",
            tempo=95,
            time_signature=(4, 4),
            tracks=[
                TrackTemplate(
                    name="Kick",
                    type="midi",
                    devices=["Drum Rack", "Saturator"],
                    settings={"warm": True}
                ),
                TrackTemplate(
                    name="Snare",
                    type="midi",
                    devices=["Drum Rack", "EQ Eight"],
                    settings={"crack": True}
                ),
                TrackTemplate(
                    name="Hi-Hats",
                    type="midi",
                    devices=["Drum Rack"],
                    settings={"swing": True}
                ),
                TrackTemplate(
                    name="Bass",
                    type="midi",
                    devices=["Operator"],
                    settings={"sub": True}
                ),
                TrackTemplate(
                    name="Sample",
                    type="audio",
                    devices=["EQ Eight", "Saturator"],
                    settings={"vinyl_warmth": True}
                ),
                TrackTemplate(
                    name="Keys",
                    type="midi",
                    devices=["Electric"],
                    settings={}
                ),
            ],
            return_tracks=[
                TrackTemplate(
                    name="Vinyl",
                    type="return",
                    devices=["Vinyl Distortion", "EQ Eight"],
                    settings={}
                ),
                TrackTemplate(
                    name="Reverb",
                    type="return",
                    devices=["Reverb"],
                    settings={"room": True}
                ),
            ],
            master_devices=["EQ Eight", "Compressor"],
            tips=[
                "Add swing to drums",
                "Use vinyl saturation for warmth",
                "Leave space for vocals",
                "Sample chops add character",
                "Layer kicks for punch"
            ]
        )
        
        # EDM Template
        self.templates["edm"] = ProjectTemplate(
            name="EDM Track",
            genre="edm",
            description="Electronic dance music template with sidechain focus",
            tempo=128,
            time_signature=(4, 4),
            tracks=[
                TrackTemplate(
                    name="Kick",
                    type="midi",
                    devices=["Drum Rack"],
                    settings={"punchy": True}
                ),
                TrackTemplate(
                    name="Clap",
                    type="midi",
                    devices=["Drum Rack", "Reverb"],
                    settings={}
                ),
                TrackTemplate(
                    name="Hi-Hats",
                    type="midi",
                    devices=["Drum Rack"],
                    settings={}
                ),
                TrackTemplate(
                    name="Bass",
                    type="midi",
                    devices=["Serum", "Compressor"],
                    settings={"sidechain": True}
                ),
                TrackTemplate(
                    name="Lead",
                    type="midi",
                    devices=["Wavetable"],
                    settings={"bright": True}
                ),
                TrackTemplate(
                    name="Pad",
                    type="midi",
                    devices=["Wavetable", "Chorus"],
                    settings={"wide": True}
                ),
                TrackTemplate(
                    name="Riser",
                    type="audio",
                    devices=["Auto Filter"],
                    settings={}
                ),
                TrackTemplate(
                    name="FX",
                    type="audio",
                    devices=[],
                    settings={}
                ),
            ],
            return_tracks=[
                TrackTemplate(
                    name="Reverb",
                    type="return",
                    devices=["Reverb"],
                    settings={"large": True}
                ),
                TrackTemplate(
                    name="Delay",
                    type="return",
                    devices=["Ping Pong Delay"],
                    settings={"sync": True}
                ),
                TrackTemplate(
                    name="Sidechain",
                    type="return",
                    devices=["Compressor"],
                    settings={"sidechain_from_kick": True}
                ),
            ],
            master_devices=["EQ Eight", "Multiband Dynamics", "Limiter"],
            tips=[
                "Heavy sidechain on bass and pads",
                "Build tension with risers",
                "Wide stereo field on synths",
                "Keep kick punchy and clear",
                "Layer sounds for impact on drops"
            ]
        )
        
        # Pop Template
        self.templates["pop"] = ProjectTemplate(
            name="Pop Track",
            genre="pop",
            description="Modern pop production template with vocal focus",
            tempo=120,
            time_signature=(4, 4),
            tracks=[
                TrackTemplate(
                    name="Drums",
                    type="midi",
                    devices=["Drum Rack", "Compressor"],
                    settings={}
                ),
                TrackTemplate(
                    name="Bass",
                    type="midi",
                    devices=["Operator"],
                    settings={}
                ),
                TrackTemplate(
                    name="Piano",
                    type="midi",
                    devices=["Grand Piano"],
                    settings={}
                ),
                TrackTemplate(
                    name="Synth",
                    type="midi",
                    devices=["Wavetable"],
                    settings={}
                ),
                TrackTemplate(
                    name="Strings",
                    type="midi",
                    devices=["Orchestral Strings"],
                    settings={}
                ),
                TrackTemplate(
                    name="Lead Vocal",
                    type="audio",
                    devices=["EQ Eight", "Compressor", "De-esser"],
                    settings={"lead": True}
                ),
                TrackTemplate(
                    name="BGV",
                    type="audio",
                    devices=["EQ Eight", "Compressor"],
                    settings={}
                ),
            ],
            return_tracks=[
                TrackTemplate(
                    name="Vocal Verb",
                    type="return",
                    devices=["Reverb"],
                    settings={"plate": True}
                ),
                TrackTemplate(
                    name="Vocal Delay",
                    type="return",
                    devices=["Simple Delay"],
                    settings={"1/4": True}
                ),
            ],
            master_devices=["EQ Eight", "Compressor", "Limiter"],
            tips=[
                "Keep vocals upfront and clear",
                "Polish the mix",
                "Wide stereo image",
                "Well-defined low end",
                "Catchy hooks are key"
            ]
        )
    
    def get_template(self, genre: str) -> Optional[ProjectTemplate]:
        """Get a template by genre"""
        return self.templates.get(genre.lower())
    
    def list_templates(self) -> List[str]:
        """List available template names"""
        return list(self.templates.keys())
    
    def get_tips_for_genre(self, genre: str) -> List[str]:
        """Get production tips for a genre"""
        template = self.templates.get(genre.lower())
        if template:
            return template.tips
        return []
    
    def get_tempo_for_genre(self, genre: str) -> Optional[float]:
        """Get typical tempo for a genre"""
        template = self.templates.get(genre.lower())
        if template:
            return template.tempo
        return None
    
    def get_track_layout(self, genre: str) -> List[Dict]:
        """Get the track layout for a template"""
        template = self.templates.get(genre.lower())
        if not template:
            return []
        
        layout = []
        for i, track in enumerate(template.tracks):
            layout.append({
                "index": i,
                "name": track.name,
                "type": track.type,
                "devices": track.devices,
                "settings": track.settings
            })
        return layout


# Global template manager
template_manager = TemplateManager()


# Data model

See [contract](contracts/illustrator-svg.md) for exact fields, APIs and bounds.
Original root attrs and effective viewport attrs are distinct immutable facts. XMP never rewrites
source text. Report schema2 records original positive percent tokens and migrates existing schema1.
SvgCssRule is immutable offline cascade evidence; no DOM or external resource escapes importers.
SvgClip is an application with shared subtree identity, reference frame and bounded local shapes.
SvgElement records visible layer path and inherited application chain; definition shapes cannot
carry clips. SvgRendered retains original transformed paths alongside final clipped material.
No global cache, machine state or persistent clip serialization is introduced.

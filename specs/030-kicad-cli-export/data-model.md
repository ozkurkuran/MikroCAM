# Data model
TransferFile(name,kind,role,sha256,byte_count); TransferManifest(schema=1,board_name,board_sha256,kicad_version,units=MM,origin=absolute,files,skipped_empty,drc_sha256,drc_errors,drc_warnings,drc_unconnected).
Archive exactly manifest.json,drc.json,files/<name>. No absolute/internal-directory member paths or external pointers. JSON duplicate keys/unknown keys rejected. Version changes require a new decoder and migration; schema1 rejects future versions.

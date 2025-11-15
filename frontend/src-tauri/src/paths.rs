use std::path::PathBuf;

/// Parse Steam's libraryfolders.vdf to find all Steam library locations
fn parse_steam_library_folders() -> Vec<PathBuf> {
    let mut libraries = Vec::new();

    let vdf_path = if cfg!(target_os = "windows") {
        PathBuf::from("C:\\Program Files (x86)\\Steam\\steamapps\\libraryfolders.vdf")
    } else if cfg!(target_os = "macos") {
        let home = std::env::var("HOME").unwrap_or_default();
        PathBuf::from(&home).join("Library/Application Support/Steam/steamapps/libraryfolders.vdf")
    } else {
        // Linux
        let home = std::env::var("HOME").unwrap_or_default();
        PathBuf::from(&home).join(".steam/steam/steamapps/libraryfolders.vdf")
    };

    if !vdf_path.exists() {
        return libraries;
    }

    // Read and parse the VDF file
    if let Ok(content) = std::fs::read_to_string(&vdf_path) {
        // Simple parser for VDF format - look for "path" entries
        for line in content.lines() {
            let trimmed = line.trim();
            if trimmed.starts_with("\"path\"") {
                // Extract path between quotes after "path"
                // Format: "path"		"/path/to/library"
                if let Some(path_start) = trimmed.rfind('"') {
                    if let Some(second_quote) = trimmed[..path_start].rfind('"') {
                        let path_str = &trimmed[second_quote + 1..path_start];
                        // On Windows, VDF uses escaped backslashes
                        let clean_path = path_str.replace("\\\\", "\\");
                        libraries.push(PathBuf::from(clean_path));
                    }
                }
            }
        }
    }

    libraries
}

/// Get all possible Steam bundle paths for Football Manager
fn get_steam_bundle_paths() -> Vec<PathBuf> {
    let mut paths = Vec::new();
    let libraries = parse_steam_library_folders();

    // Game names to check (FM 26 vs FM 2026)
    let game_names = vec!["Football Manager 26", "Football Manager 2026"];

    if cfg!(target_os = "windows") {
        // Windows: data/StreamingAssets/aa/StandaloneWindows64
        for library in &libraries {
            let common_path = library.join("steamapps/common");
            for game_name in &game_names {
                paths.push(
                    common_path
                        .join(game_name)
                        .join("data/StreamingAssets/aa/StandaloneWindows64"),
                );
            }
        }
        // Default Steam locations
        for game_name in &game_names {
            paths.extend(vec![
                PathBuf::from("C:\\Program Files (x86)\\Steam\\steamapps\\common")
                    .join(game_name)
                    .join("data/StreamingAssets/aa/StandaloneWindows64"),
                PathBuf::from("C:\\Program Files\\Steam\\steamapps\\common")
                    .join(game_name)
                    .join("data/StreamingAssets/aa/StandaloneWindows64"),
            ]);
        }
    } else if cfg!(target_os = "macos") {
        // macOS: Two variants - fm.app and fm_Data
        for library in &libraries {
            let common_path = library.join("steamapps/common");
            for game_name in &game_names {
                let base = common_path.join(game_name);
                paths.push(
                    base.join("fm.app/Contents/Resources/Data/StreamingAssets/aa/StandaloneOSX"),
                );
                paths.push(base.join("fm_Data/StreamingAssets/aa/StandaloneOSXUniversal"));
            }
        }
        // Default Steam location
        let home = std::env::var("HOME").unwrap_or_default();
        for game_name in &game_names {
            let base = PathBuf::from(&home)
                .join("Library/Application Support/Steam/steamapps/common")
                .join(game_name);
            paths
                .push(base.join("fm.app/Contents/Resources/Data/StreamingAssets/aa/StandaloneOSX"));
            paths.push(base.join("fm_Data/StreamingAssets/aa/StandaloneOSXUniversal"));
        }
    } else {
        // Linux: fm_Data/StreamingAssets/aa/StandaloneLinux64
        for library in &libraries {
            let common_path = library.join("steamapps/common");
            for game_name in &game_names {
                paths.push(
                    common_path
                        .join(game_name)
                        .join("fm_Data/StreamingAssets/aa/StandaloneLinux64"),
                );
            }
        }
        // Default Steam locations
        let home = std::env::var("HOME").unwrap_or_default();
        for game_name in &game_names {
            paths.extend(vec![
                PathBuf::from(&home)
                    .join(".steam/steam/steamapps/common")
                    .join(game_name)
                    .join("fm_Data/StreamingAssets/aa/StandaloneLinux64"),
                PathBuf::from(&home)
                    .join(".local/share/Steam/steamapps/common")
                    .join(game_name)
                    .join("fm_Data/StreamingAssets/aa/StandaloneLinux64"),
            ]);
        }
        // Steam Deck
        paths.push(PathBuf::from("/run/media/mmcblk0p1/steamapps/common/Football Manager 26/fm_Data/StreamingAssets/aa/StandaloneLinux64"));
    }

    paths
}

/// Get all possible Epic Games bundle paths
fn get_epic_bundle_paths() -> Vec<PathBuf> {
    let mut paths = Vec::new();
    let game_names = vec![
        "FootballManager26",
        "FootballManager2026",
        "Football Manager 26",
    ];

    if cfg!(target_os = "windows") {
        // Windows Epic: data/StreamingAssets/aa/StandaloneWindows64
        for game_name in &game_names {
            paths.extend(vec![
                PathBuf::from("C:\\Program Files\\Epic Games")
                    .join(game_name)
                    .join("data/StreamingAssets/aa/StandaloneWindows64"),
                PathBuf::from("C:\\Program Files (x86)\\Epic Games")
                    .join(game_name)
                    .join("data/StreamingAssets/aa/StandaloneWindows64"),
            ]);
        }
    } else if cfg!(target_os = "macos") {
        // macOS Epic: fm_Data/StreamingAssets/aa/StandaloneOSXUniversal
        let home = std::env::var("HOME").unwrap_or_default();
        paths.push(PathBuf::from(&home).join("Library/Application Support/Epic/Football Manager 26/fm_Data/StreamingAssets/aa/StandaloneOSXUniversal"));
        for game_name in &game_names {
            paths.extend(vec![
                PathBuf::from(&home).join(format!("Library/Application Support/Epic/{}/fm_Data/StreamingAssets/aa/StandaloneOSXUniversal", game_name)),
            ]);
        }
    } else {
        // Linux Epic via Heroic: fm_Data/StreamingAssets/aa/StandaloneLinux64
        let home = std::env::var("HOME").unwrap_or_default();
        for game_name in &game_names {
            paths.extend(vec![
                PathBuf::from(&home).join(format!("Games/Heroic/{}/fm_Data/StreamingAssets/aa/StandaloneLinux64", game_name)),
                PathBuf::from(&home).join(format!(".var/app/com.heroicgameslauncher.hgl/Games/{}/fm_Data/StreamingAssets/aa/StandaloneLinux64", game_name)),
            ]);
        }
        paths.push(
            PathBuf::from(&home)
                .join("Games/football-manager-26/fm_Data/StreamingAssets/aa/StandaloneLinux64"),
        );
        paths.push(
            PathBuf::from(&home)
                .join("Games/football-manager-2026/fm_Data/StreamingAssets/aa/StandaloneLinux64"),
        );
    }

    paths
}

/// Get all possible Xbox Game Pass bundle paths (Windows only)
fn get_xbox_bundle_paths() -> Vec<PathBuf> {
    let mut paths = Vec::new();

    if cfg!(target_os = "windows") {
        // Static paths with bundle subdirectory
        paths.extend(vec![
            PathBuf::from("C:\\Program Files\\WindowsApps\\SEGA.FootballManager26")
                .join("data/StreamingAssets/aa/StandaloneWindows64"),
            PathBuf::from("C:\\Program Files\\WindowsApps\\SEGA.FootballManager2026")
                .join("data/StreamingAssets/aa/StandaloneWindows64"),
        ]);

        // Dynamic search for versioned folders
        if let Ok(entries) = std::fs::read_dir("C:\\Program Files\\WindowsApps") {
            for entry in entries.flatten() {
                let path = entry.path();
                if let Some(name) = path.file_name() {
                    let name_str = name.to_string_lossy();
                    if name_str.contains("SEGA.FootballManager26")
                        || name_str.contains("SEGA.FootballManager2026")
                    {
                        paths.push(path.join("data/StreamingAssets/aa/StandaloneWindows64"));
                    }
                }
            }
        }
    }

    paths
}

#[tauri::command]
pub fn detect_game_installation() -> Option<String> {
    // Gather all possible bundle paths from all sources
    let mut possible_paths: Vec<PathBuf> = Vec::new();

    possible_paths.extend(get_steam_bundle_paths());
    possible_paths.extend(get_epic_bundle_paths());
    possible_paths.extend(get_xbox_bundle_paths());

    // Check each path and return the first one that exists
    for path in possible_paths {
        if path.exists() {
            return Some(path.to_string_lossy().to_string());
        }
    }

    None
}

#[tauri::command]
pub fn find_bundles_in_game_dir(game_dir: String) -> Option<String> {
    let game_path = PathBuf::from(game_dir);

    // Platform-specific bundle paths relative to game root
    let bundle_subdirs = if cfg!(target_os = "windows") {
        vec!["data/StreamingAssets/aa/StandaloneWindows64"]
    } else if cfg!(target_os = "macos") {
        vec![
            "fm.app/Contents/Resources/Data/StreamingAssets/aa/StandaloneOSX",
            "fm_Data/StreamingAssets/aa/StandaloneOSXUniversal",
        ]
    } else {
        vec!["fm_Data/StreamingAssets/aa/StandaloneLinux64"]
    };

    for subdir in bundle_subdirs {
        let bundles_path = game_path.join(subdir);
        if bundles_path.exists() {
            return Some(bundles_path.to_string_lossy().to_string());
        }
    }

    None
}

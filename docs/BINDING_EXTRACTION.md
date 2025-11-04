# UXML Data Binding Extraction

## Overview

FM's UI system uses **data bindings** to connect UI elements to game data at runtime. We can now extract these bindings from Unity bundles!

## What Are Bindings?

Bindings tell UI elements what game data to display or react to:

```
SIText element → TextBinding: "Player.Name" → displays the player's name
SIVisible element → Binding: "Club.ReservesTeam" → shows/hides based on if club has a reserves team
```

## Types of Bindings Extracted

### 1. BindingRemapper
**Purpose**: Remaps binding variable names to actual data paths

**Example**:
```
BindingRemapper:
  Mappings:
    - team -> ActualFixture.HomeTeam
    - kittype -> ActualFixture.KitShirtStyle
    - MatchHomeTeamKit -> Team.Kit
    - ishometeam -> const.True
```

This means when a child element references `team`, it actually gets `ActualFixture.HomeTeam`.

### 2. BindingExpect
**Purpose**: Declares what data must be provided to this UXML component

**Example**:
```
BindingExpect:
  Parameters:
    - club
    - person
    - fixture
    - isonmainscreen
```

This is like function parameters - the UXML file expects these data objects to be passed in.

### 3. BindingVariables
**Purpose**: Declares local variables for internal component state

**Example**:
```
BindingVariables:
  ValueVariables:
    - selectedtab
    - mainteamtab
    - teamsindex
```

These are like local variables in the component's scope.

### 4. Component-Level Bindings

#### SIText (Text Display)
```
SIText:
  name: player-name-text
  TextBinding: Player.Name
```

#### SIVisible (Show/Hide)
```
SIVisible:
  name: has-reserves
  Binding: Club.ReservesTeam
```

#### SIEnabled (Enable/Disable)
```
SIEnabled:
  name: submit-button
  Binding: Form.IsValid
```

#### BindableSwitchElement (Conditional Display)
```
BindableSwitchElement:
  name: IsGoalkeeperSwitch
  Binding: Person.IsGoalkeeper
```

#### StreamedObjectList (List Display)
```
StreamedObjectList:
  name: player-list
  Binding: Team.Players
  SelectedItemsBinding: selectedplayers
```

#### SIButton (Interactive Button)
```
SIButton:
  HoverBinding: TileInteraction
  Events: [click handlers]
```

## Real-World Examples

### Example 1: Player Attributes Tile
```
File: PlayerAttributesTile
Bindings: 8

BindingRemapper:
  Mappings:
    - person -> binding
    - player -> binding

BindingExpect:
  Parameters:
    - isonmainscreen

SIText (title-text):
  TextBinding: [determined at runtime based on person mapping]

BindableSwitchElement (IsGoalkeeperSwitch):
  Binding: Person.IsGoalkeeper
```

### Example 2: Match Stats Block
```
File: MatchStatsKeyStatsBlock
Bindings: 12

BindingExpect:
  Parameters:
    - fixture
    - match

BindingRemapper (HomeTeam):
  Mappings:
    - team -> ActualFixture.HomeTeam
    - kittype -> ActualFixture.KitShirtStyle
    - ishometeam -> const.True
    - HomeTeamStats -> ActualFixture.Stats

BindingRemapper (AwayTeam):
  Mappings:
    - team -> ActualFixture.AwayTeam
    - ishometeam -> const.False

SIText:
  TextBinding: ActualFixture.HomeTeam.Name

SIText:
  TextBinding: HomeTeamStats.TotalShots
```

### Example 3: Club Info Block
```
File: ClubInfoDataBlock
Bindings: 79

BindingExpect:
  Parameters:
    - club

SIText:
  TextBinding: Club.Background

SIVisible (second-team-visible):
  Binding: Club.ReservesTeam

SIText (reserves team name):
  TextBinding: Club.ReservesTeam.Name

BindingRemapper:
  Mappings:
    - team -> Club.MainTeam

SIVisible (HasDivision):
  Binding: team.Division
```

## Data Path Structure

Based on extracted bindings, here are common data paths:

### Player Data
- `Player.Name`
- `Player.IsGoalkeeper`
- `Person.Name`
- `Person.Age`
- `Person.IsGoalkeeper`

### Club/Team Data
- `Club.Name`
- `Club.Background`
- `Club.MainTeam`
- `Club.ReservesTeam`
- `Club.YouthTeam`
- `Club.ReservesTeam.Name`
- `Club.YouthTeam.Name`
- `Team.Name`
- `Team.Players`
- `Team.Kit`
- `Team.Division`

### Match/Fixture Data
- `Fixture.HomeTeam`
- `Fixture.AwayTeam`
- `ActualFixture.HomeTeam`
- `ActualFixture.AwayTeam`
- `ActualFixture.KitShirtStyle`
- `ActualFixture.Stats`
- `HomeTeamStats.TotalShots`
- `AwayTeamStats.TotalShots`

### Special Values
- `const.True` - constant true value
- `const.False` - constant false value
- `const.NullRef` - null reference
- `human.Team` - the player's managed team
- `game.GameManagers` - game manager list
- `app.store.CanAddIgeToCart` - app-level state

## How to Use This Information

### For Skin Modders
1. **Understanding Data Flow**: You now know where UI elements get their data
2. **Debugging**: If text isn't showing, check if the binding path is correct
3. **Customization**: You can see which elements are data-driven vs static
4. **Requirements**: BindingExpect shows what data a component needs to work

### For Advanced Modding
- You **cannot** change bindings (they're in C# DLLs)
- You **can** understand which elements will update dynamically
- You **can** see which switches (BindableSwitchElement) control visibility
- You **can** create custom UXML layouts knowing what data is available

## Files with Most Bindings

Top 10 files by binding count (from ui-tiles_assets_all.bundle):

1. **FeedbackMatchBlock**: 122 bindings
   - 28 BindingRemapper instances
   - 7 BindingExpect instances
   - Complex match feedback UI

2. **GameCreationClubSelectionBlock**: 89 bindings
   - 22 BindingVariables (lots of internal state)
   - 17 BindingRemapper instances
   - Club selection in game setup

3. **ContractTermsCombinedBlock**: 87 bindings
   - Contract negotiation UI
   - Multiple data remapping layers

4. **ClubInfoDataBlock**: 79 bindings
   - 21 SIText instances showing club data
   - Tabbed interface with multiple binding layers

5. **PlayerAnalyticsBlock_16x8**: 65+ bindings
   - Complex analytics visualization
   - Team and player data analysis

## Statistics

From **ui-tiles_assets_all.bundle** (2,681 UXML files):
- **2,658 files** have bindings (99%)
- **Average**: 8-12 bindings per file
- **Maximum**: 122 bindings (FeedbackMatchBlock)
- **Most common**: BindingRemapper (data path mapping)

## Technical Details

### Extraction Method
1. Access Unity's `ManagedReferencesRegistry` in VisualTreeAsset
2. Parse `RefIds` array containing `UxmlSerializedData` for each element
3. Extract binding fields from serialized data:
   - Direct `m_path` values (simple bindings)
   - `m_direct.m_path` (BindingMethod → BindingPath)
   - `m_visualFunction` (function-based bindings)
   - Special arrays (Mappings, Parameters, ValueVariables)

### Limitations
1. **Runtime-Only**: Some bindings are created at runtime in C# code
2. **Function Bindings**: Visual functions show name but not implementation
3. **Complex Expressions**: Some bindings use C# expressions we can't see
4. **Binding Context**: We see the path but not always what type of object it expects

## Future Enhancements

Possible additions to binding extraction:
1. **Binding Documentation**: Match paths to FM object types
2. **Dependency Graph**: Show which UXML files share data
3. **Missing Bindings**: Detect elements that should have bindings
4. **Binding Validation**: Check if paths are valid
5. **Interactive Explorer**: Browse bindings in web interface

## Catalog Integration

Bindings are now included in the UXML catalog:

```json
{
  "uxml_files": {
    "PlayerAttributesTile": {
      "binding_count": 8,
      "bindings": [
        {
          "rid": 1000,
          "type": "SI.Bindable.BindingRemapper/UxmlSerializedData",
          "name": "",
          "bindings": {
            "Mappings": [
              "person -> binding",
              "player -> binding"
            ]
          }
        },
        {
          "rid": 1010,
          "type": "SI.Bindable.SIText/UxmlSerializedData",
          "name": "title-text",
          "bindings": {
            "TextBinding": "TileText"
          }
        }
      ]
    }
  }
}
```

## Conclusion

**Yes, we can extract binding data!** 🎉

You now have visibility into:
- What data each UI element displays
- How data paths are remapped between components
- What parameters UXML templates require
- Which elements are conditionally shown/hidden

This makes FM's UI system much more understandable for skin developers!

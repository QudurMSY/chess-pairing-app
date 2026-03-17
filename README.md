# Chess Pairing App

A comprehensive chess tournament pairing application that tries to implement multiple FIDE-approved pairing systems for both individual and team tournaments.

## Features

- **Multiple Pairing Systems**:
  - Swiss System
  - Berger Table (Round-Robin)
  - Varma Table (Restricted Drawing)
  - Burstein System
  - Dubov System
  - Lim System
  - Double Swiss System
  - Swiss Team Pairing System

- **Tie-Break Systems**:
  - Buchholz
  - Sonneborn-Berger
  - Direct Encounter

- **Player and Team Management**:
  - Player registration with Elo ratings
  - Bulk player import via CSV
  - Team registration and management
  - Round and result management
  - Squad lineup management

- **Reporting**:
  - Generate comprehensive tournament reports
  - Export final standings, team statistics, and player performance
  - HTML format with embedded styling

- **Performance**:
  - Optimized for large tournaments (256+ players)
  - Efficient database operations

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/QudurMSY/chess-pairing-app.git
   cd chess-pairing-app
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```

## Usage

### Player Registration
- Register players with their names and Elo ratings
- Import players from a CSV file
- Assign players to tournaments

### Tournament Management
- Create tournaments with different pairing systems
- Manage rounds and enter match results using the sequential board entry
- View pairings, standings, and generate HTML reports

### Team Tournaments
- Create and manage teams
- Register players to teams
- Manage squad lineups before rounds
- Use Swiss Team Pairing System for team competitions

## Testing

Run the test scripts to verify the functionality using pytest:

```bash
pytest tests/
```

Individual tests can be run as well:
```bash
pytest tests/test_app.py
pytest tests/test_large_tournament.py
pytest tests/test_berger_varma.py
pytest tests/test_reporting.py
pytest tests/test_player_import.py
```

## Project Structure

```
chess-pairing-app/
├── main.py                     # Main entry point
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
├── chess_pairing.db            # SQLite database
├── src/
│   ├── core/                   # Core functionality
│   │   ├── player_manager.py   # Player management
│   │   ├── tournament_manager.py # Tournament management
│   │   ├── team_manager.py     # Team management
│   │   ├── round_manager.py    # Round and result management
│   │   ├── team_pairing.py     # Team pairing logic
│   │   ├── tie_break.py        # Tie-break systems
│   │   ├── reporting.py        # Tournament reporting generation
│   │   ├── player.py           # Core player model
│   │   └── pairing/            # Pairing systems
│   │       ├── pairing_generator.py # Shared generation logic
│   │       ├── swiss_pairing.py
│   │       ├── berger_table.py
│   │       ├── varma_table.py
│   │       ├── burstein_system.py
│   │       ├── dubov_system.py
│   │       ├── lim_system.py
│   │       └── double_swiss_system.py
│   ├── database/               # Database operations
│   │   └── database.py         # SQLite database management
│   ├── memory/                 # Context and metadata storage
│   │   └── memory_bank.py      
│   └── ui/                     # User interface
│       ├── main_window.py      # Main application window
│       ├── player_registration.py # Player creation and import
│       ├── tournament_management.py # Tournament operations
│       ├── round_management.py # Round controls and standings
│       ├── tournament_creator.py # Creation dialog
│       ├── tournament_manager_ui.py # Main interface tabs
│       ├── board_result_entry.py # Match result entry
│       ├── lineup_management.py # Team lineups
│       ├── squad_management.py  # Team squads
│       └── style.qss           # Application styling
├── tests/                      # Pytest suite
│   ├── test_app.py             # Basic functionality
│   ├── test_large_tournament.py # Large scale performance
│   ├── test_berger_varma.py    # Round-Robin systems
│   ├── test_pairing_systems.py # Alternative pairing tests
│   ├── test_fide_compliance.py # FIDE rules checks
│   ├── test_player_import.py   # CSV importing
│   └── ...                     # Additional test modules
└── fide_rules/                 # FIDE regulations and rules
```

## Technologies Used

- **Python**: Core programming language
- **PyQt5**: GUI framework for the desktop application
- **SQLite**: Lightweight database for data storage
- **pytest**: Testing framework

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For any questions or feedback, please contact the project maintainer.

---

**Note**: This application is designed to comply with FIDE regulations for chess tournaments. Always verify the pairing rules and tie-break systems with the official FIDE regulations before using this app in official tournaments.

**Note**: This application is completely vibecoded. 

import os
import tempfile
import pandas as pd
from datetime import datetime

# Textual imports for the Terminal UI
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Input, Button, RichLog, ProgressBar, DataTable, TabbedContent, TabPane, Static
from textual.containers import Vertical, Horizontal
from textual import work

# Data processing imports
import diyepw
from pythermalcomfort.models import heat_index_rothfusz

# =========================================================
# Pop-up Modal Screen for Final Results
# =========================================================
class ResultsModal(ModalScreen):
    """A pop-up modal to display the final target dates and file paths."""
    
    CSS = """
    ResultsModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    #results-container {
        width: 60%;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }
    .modal-header {
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }
    #close-button {
        margin-top: 1;
        width: 100%;
    }
    """

    def __init__(self, results_text: str):
        super().__init__()
        self.results_text = results_text

    def compose(self) -> ComposeResult:
        with Vertical(id="results-container"):
            yield Static("PIPELINE EXECUTION COMPLETE", classes="modal-header")
            yield Static(self.results_text, id="results-text")
            yield Button("Close", id="close-button", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-button":
            self.app.pop_screen()

# =========================================================
# Main Pipeline Application
# =========================================================
class WeatherPipelineApp(App):
    """A Textual App to handle EPW Generation and Processing seamlessly."""

    TITLE = "DIYEPW Advanced Pipeline"
    
    CSS = """
    Input {
        margin-bottom: 1;
    }
    #run-button {
        width: 100%;
        margin-top: 1;
        margin-bottom: 1;
    }
    RichLog {
        border: solid green;
        height: 1fr;
        background: $surface-darken-1;
    }
    .input-row {
        height: auto;
    }
    /* Force exactly 50% width on these specific horizontal inputs */
    #start_year, #end_year, #winter_temp, #summer_temp {
        width: 50%;
    }
    #progress-bar {
        margin-bottom: 1;
    }
    #data-table {
        height: 1fr;
        border: solid blue;
    }
    """

    def __init__(self):
        super().__init__()
        self.final_df = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        
        with TabbedContent(initial="tab-setup", id="tabs"):
            
            # TAB 1: Inputs and Controls
            with TabPane("1. Setup & Run", id="tab-setup"):
                with Vertical():
                    yield Input(id="wmo", placeholder="WMO Station IDs (comma separated)", value="744860")
                    
                    with Horizontal(classes="input-row"):
                        yield Input(id="start_year", placeholder="Start Year", value="1970", type="integer")
                        yield Input(id="end_year", placeholder="End Year", value="2025", type="integer")
                    
                    with Horizontal(classes="input-row"):
                        yield Input(id="winter_temp", placeholder="Winter Return Temp (°C)", value="20.0", type="number")
                        yield Input(id="summer_temp", placeholder="Summer Return Temp (°C)", value="24.0", type="number")
                        
                    yield Button("Run Pipeline (In-Memory)", id="run-button", variant="success")
            
            # TAB 2: Live Progress and Logs
            with TabPane("2. Logs & Progress", id="tab-logs"):
                with Vertical():
                    yield ProgressBar(id="progress-bar", show_eta=True)
                    yield RichLog(id="log-view", markup=True)
            
            # TAB 3: Data Table Preview
            with TabPane("3. Results Preview", id="tab-preview"):
                yield DataTable(id="data-table")
                
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        if event.button.id == "run-button":
            # Extract basic data
            wmo_str = self.query_one("#wmo", Input).value
            try:
                start_year = int(self.query_one("#start_year", Input).value)
                end_year = int(self.query_one("#end_year", Input).value)
                wmo_list = [int(x.strip()) for x in wmo_str.split(",")]
                years = list(range(start_year, end_year + 1))
                
                # Extract Temperatures
                winter_temp = float(self.query_one("#winter_temp", Input).value)
                summer_temp = float(self.query_one("#summer_temp", Input).value)
                
            except ValueError:
                self.query_one("#tabs", TabbedContent).active = "tab-logs"
                self.query_one("#log-view", RichLog).write("[bold red]Error: Ensure WMO, Years, and Temperatures are valid numbers.[/]")
                return

            self.query_one("#run-button", Button).disabled = True
            self.query_one("#tabs", TabbedContent).active = "tab-logs"
            self.set_timer(0.1, lambda: self.run_pipeline(wmo_list, years, winter_temp, summer_temp))

    def update_table(self, df):
        """Helper to populate the DataTable UI widget safely from the main thread."""
        table = self.query_one("#data-table", DataTable)
        table.clear(columns=True)
        table.add_columns(*df.columns.tolist())
        rows = df.head(20).astype(str).values.tolist()
        table.add_rows(rows)

    def show_modal(self, message: str):
        """Pushes the pop-up modal to the screen."""
        self.push_screen(ResultsModal(message))

    @work(exclusive=True, thread=True)
    def run_pipeline(self, wmo_list, years, winter_temp, summer_temp):
        """Background worker to process the EPWs."""
        
        log = self.query_one("#log-view", RichLog)
        progress_bar = self.query_one("#progress-bar", ProgressBar)

        def write_log(message):
            self.call_from_thread(log.write, message)

        write_log("\n[bold cyan]========================================[/]")
        write_log("[bold cyan] Starting In-Memory EPW Pipeline...[/]")
        write_log("[bold cyan]========================================[/]")

        total_downloads = len(years) * len(wmo_list)
        self.call_from_thread(progress_bar.update, total=total_downloads, progress=0)

        all_dfs = []

        with tempfile.TemporaryDirectory() as temp_epw_dir:
            write_log(f"\n[bold yellow]--- Step 1: Generating AMY EPWs ---[/]")
            
            for year in years:
                for wmo in wmo_list:
                    try:
                        write_log(f"Fetching WMO {wmo} for Year {year}...")
                        diyepw.create_amy_epw_files_for_years_and_wmos(
                            [year], [wmo],
                            max_records_to_interpolate=10,
                            max_missing_amy_rows=300,
                            allow_downloads=True,
                            amy_epw_dir=temp_epw_dir
                        )
                        write_log(f"[green]  -> Downloaded: WMO {wmo}, Year {year}[/]")
                    except Exception as e:
                        write_log(f"[red]  -> Skipped/Error: WMO {wmo}, Year {year} -> {e}[/]")
                    
                    self.call_from_thread(progress_bar.advance, 1)

            write_log("\n[bold yellow]--- Step 2: Extracting Temp EPWs to DataFrame ---[/]")
            
            epw_cols = [0, 1, 2, 3, 4, 6, 7, 8, 13]
            col_names = [
                "Year", "Month", "Day", "Hour", "Minute",
                "Dry Bulb Temperature {C}", "Dew Point Temperature {C}",
                "Relative Humidity {%}", "Global Horizontal Radiation {Wh/m2}"
            ]

            for filename in os.listdir(temp_epw_dir):
                if filename.endswith('.epw'):
                    filepath = os.path.join(temp_epw_dir, filename)
                    try:
                        df = pd.read_csv(filepath, skiprows=8, header=None, usecols=epw_cols, names=col_names)
                        df['SourceFile'] = filename
                        all_dfs.append(df)
                        write_log(f"Mapped to memory: {filename}")
                    except Exception as e:
                        write_log(f"[red]Error parsing {filename}: {e}[/]")
                        
        if not all_dfs:
            write_log("[bold red]Fatal Error: No valid EPW files found or generated. Aborting.[/]")
            self.call_from_thread(lambda: setattr(self.query_one("#run-button", Button), "disabled", False))
            return

        combined_df = pd.concat(all_dfs, ignore_index=True)

        time_df = pd.DataFrame({
            'year': combined_df['Year'], 'month': combined_df['Month'],
            'day': combined_df['Day'], 'hour': combined_df['Hour'] - 1 
        })
        combined_df["Date"] = pd.to_datetime(time_df)
        combined_df["HH:MM"] = combined_df["Hour"].astype(str).str.zfill(2) + ":00"

        # ---------------------------------------------------------
        # Step 3: Heat Index & Rolling Averages
        # ---------------------------------------------------------
        write_log("\n[bold yellow]--- Step 3: Computing Metrics & Rolling Averages ---[/]")
        
        cols_to_keep = [
            "Date", "HH:MM", "Dry Bulb Temperature {C}",
            "Dew Point Temperature {C}", "Relative Humidity {%}",
            "Global Horizontal Radiation {Wh/m2}"
        ]
        df = combined_df[cols_to_keep].dropna().copy()
        df = df.sort_values(by="Date").reset_index(drop=True)

        write_log("Calculating Heat Index...")
        def calc_hi(row):
            try:
                res = heat_index_rothfusz(tdb=float(row["Dry Bulb Temperature {C}"]), rh=float(row["Relative Humidity {%}"]))
                return float(res["hi"]) if isinstance(res, dict) else float(res)
            except:
                return None
        df['Heat Index'] = df.apply(calc_hi, axis=1)

        write_log("Ensuring data types are numeric...")
        numeric_cols = [
            "Dry Bulb Temperature {C}", "Dew Point Temperature {C}", 
            "Relative Humidity {%}", "Global Horizontal Radiation {Wh/m2}", "Heat Index"
        ]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        write_log("Calculating 168-hour Rolling Windows...")
        indexer = pd.api.indexers.FixedForwardWindowIndexer(window_size=168)
        
        db_col, dp_col, hi_col, ghr_col = numeric_cols[0], numeric_cols[1], numeric_cols[4], numeric_cols[3]

        df["rolling average DBt"] = df[db_col].rolling(window=indexer, min_periods=1).mean()
        df["rolling average DPt"] = df[dp_col].rolling(window=indexer, min_periods=1).mean()
        df["rolling heat index"] = df[hi_col].rolling(window=indexer, min_periods=1).mean()
        df["rolling GHR"] = df[ghr_col].rolling(window=indexer, min_periods=1).mean()

        df["rolling max DBt"] = df[db_col].rolling(window=indexer, min_periods=1).max()
        df["rolling min DBt"] = df[db_col].rolling(window=indexer, min_periods=1).min()
        df["rolling max DPt"] = df[dp_col].rolling(window=indexer, min_periods=1).max()
        df["rolling min DPt"] = df[dp_col].rolling(window=indexer, min_periods=1).min()

        write_log("Compiling First-of-Day statistics...")
        seen_dates = set()
        first_vals = {k: [] for k in [
            "first of rolling avg dbt", "first of rolling avg dpt", "first of rolling avg HI", "first of rolling avg GHR",
            "first of rolling max DBt", "first of rolling min DBt", "first of rolling max DPt", "first of rolling min DPt", "first rolling avg date"
        ]}

        for _, row in df.iterrows():
            day_key = row["Date"].date()
            if day_key not in seen_dates:
                seen_dates.add(day_key)
                first_vals["first of rolling avg dbt"].append(row["rolling average DBt"])
                first_vals["first of rolling avg dpt"].append(row["rolling average DPt"])
                first_vals["first of rolling avg HI"].append(row["rolling heat index"])
                first_vals["first of rolling avg GHR"].append(row["rolling GHR"])
                first_vals["first of rolling max DBt"].append(row["rolling max DBt"])
                first_vals["first of rolling min DBt"].append(row["rolling min DBt"])
                first_vals["first of rolling max DPt"].append(row["rolling max DPt"])
                first_vals["first of rolling min DPt"].append(row["rolling min DPt"])
                first_vals["first rolling avg date"].append(row["Date"])

        for col_name, val_list in first_vals.items():
            df[col_name] = pd.Series(val_list).reset_index(drop=True)

        # ---------------------------------------------------------
        # Step 4: Extract Return Temp Target Dates
        # ---------------------------------------------------------
        write_log("\n[bold yellow]--- Step 4: Extracting Target Dates ---[/]")
        
        valid_firsts = df.dropna(subset=["first rolling avg date"]).copy()
        
        modal_message = ""

        # 1. Winter Search
        winter_mask = (valid_firsts["first of rolling min DBt"] >= winter_temp - 0.5) & \
                      (valid_firsts["first of rolling min DBt"] <= winter_temp + 0.5)
        winter_filtered = valid_firsts[winter_mask]
        
        if not winter_filtered.empty:
            winter_sorted = winter_filtered.sort_values(by="first of rolling avg GHR", ascending=True)
            target_winter_date = winter_sorted.iloc[0]["first rolling avg date"]
            w_msg = f"Winter Target Found: {target_winter_date.strftime('%Y-%m-%d %H:%M:%S')}\nMatches criteria: Min DBt ≈ {winter_temp}°C, Lowest GHR."
            write_log(f"[bold cyan]{w_msg}[/]")
            modal_message += f"[bold cyan]Winter Summary[/]\n{w_msg}\n\n"
        else:
            w_err = f"No dates found matching Winter Return Temp {winter_temp}°C (±0.5)."
            write_log(f"[bold red]{w_err}[/]")
            modal_message += f"[bold red]Winter Summary[/]\n{w_err}\n\n"

        # 2. Summer Search
        summer_mask = (valid_firsts["first of rolling max DBt"] >= summer_temp - 0.5) & \
                      (valid_firsts["first of rolling max DBt"] <= summer_temp + 0.5)
        summer_filtered = valid_firsts[summer_mask]
        
        if not summer_filtered.empty:
            summer_sorted = summer_filtered.sort_values(by="first of rolling avg HI", ascending=False)
            target_summer_date = summer_sorted.iloc[0]["first rolling avg date"]
            s_msg = f"Summer Target Found: {target_summer_date.strftime('%Y-%m-%d %H:%M:%S')}\nMatches criteria: Max DBt ≈ {summer_temp}°C, Highest Heat Index."
            write_log(f"[bold red]{s_msg}[/]")
            modal_message += f"[bold yellow]Summer Summary[/]\n{s_msg}\n\n"
        else:
            s_err = f"No dates found matching Summer Return Temp {summer_temp}°C (±0.5)."
            write_log(f"[bold red]{s_err}[/]")
            modal_message += f"[bold red]Summer Summary[/]\n{s_err}\n\n"

        # ---------------------------------------------------------
        # Step 5: Output and UI Updates
        # ---------------------------------------------------------
        self.final_df = df
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", prefix="DIYEPW_output_")
        temp_path = temp_file.name
        temp_file.close() 
        df.to_csv(temp_path, index=False)
        
        write_log(f"\n[bold green]Success! Data generated and processed.[/]")
        write_log(f"[bold magenta]Temporary CSV backup saved at:\n{temp_path}[/]")
        
        modal_message += f"[bold green]Data Export Location[/]\n{temp_path}"

        # Trigger UI updates safely from background thread
        self.call_from_thread(self.update_table, df) 
        self.call_from_thread(lambda: setattr(self.query_one("#run-button", Button), "disabled", False))
        
        # Trigger the Modal Pop-up
        self.call_from_thread(self.show_modal, modal_message)

if __name__ == "__main__":
    app = WeatherPipelineApp()
    app.run()
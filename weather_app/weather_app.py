import os
import tempfile
import pandas as pd
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
import sys
from contextlib import redirect_stdout, redirect_stderr
import logging

# Textual imports for the Terminal UI
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Input, Button, RichLog, ProgressBar, TabbedContent, TabPane, Static, Label, Markdown
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual import work

# Data processing imports
import diyepw
from pythermalcomfort.models import heat_index_rothfusz

# =========================================================
# ReadMe Text Definition
# =========================================================
README_TEXT = """
# Phius Resilience Weather Generator v26.1.0

### Notes

This tool has been developed by Phius to generate weather data to be used in thermal resilience simulation. It searches through the historical record available in the NOAA ISD, from 1970 to present, and generates a data frame of the entire historical record. Then, it will search for user defined nth-year return temperatures for summer and winter, filtering for weeks where the peak temperature is +- 0.5°C from the input temperature. The tie breaking element in winter is to identify a week with the lowest average global horizontal radiation; for summer it is the highest average heat index. These weeks are then merged into a user input EPW weather file that can be used in simulation.

**1.** Input the **WMO number** of the weather station you are trying to generate weather data for.

**2.** Input a **start and stop year** for the historical record to be read. Input only years between 1970 and the previous year to present. (i.e., you cannot select weather data to stop in 2025 if you are using this tool in 2025, only 1970-2024).

**3.** Input the target **return temperature in °C**. This data can be found in the ASHRAE Handbook.

**4.** Input a path for the **base EPW file** to be modified. The extreme design weeks identified will be injected into this file.

**5.** Input the **output path and name** for the resulting weather file.

**6.** Click **Generate Weather Data** to start the calculation. The calculation progress can be viewed in the second tab *Logs & Progress*.

**7.** After completion, the start dates of the identified extreme weeks will be shown. Write these down or screenshot them, and use this as the outage periods in thermal resilience simulations.
"""

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
        width: 70%;
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

    TITLE = "Phius Resilience Weather Generator"
    
    CSS = """
    .readme-container {
        padding: 1 2;
    }
    .input-label {
        text-style: bold;
        color: $secondary;
        margin-top: 1;    
        margin-bottom: 0; 
        margin-left: 1;
    }
    Input {
        margin-bottom: 0; 
    }
    #run-button {
        width: 100%;
        margin-top: 2;    
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
    .col {
        width: 1fr;
        height: auto;     
        padding-right: 1;
    }
    .file-browse-row {
        height: auto;
        margin-bottom: 0;
    }
    #tmy_file, #output_epw {
        width: 1fr;
        margin-bottom: 0;
    }
    #browse-button, #browse-save-button {
        width: 15;
        margin-left: 1;
    }
    #progress-bar {
        margin-bottom: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.final_df = None

    def compose(self) -> ComposeResult:
        yield Header()
        
        with TabbedContent(initial="tab-readme", id="tabs"):
            
            with TabPane("0. ReadMe", id="tab-readme"):
                with VerticalScroll(classes="readme-container"):
                    yield Markdown(README_TEXT)

            with TabPane("1. Setup & Run", id="tab-setup"):
                with VerticalScroll():
                    # Target WMO Row
                    yield Label("Target WMO Station ID(s) [Comma Separated]", classes="input-label")
                    yield Input(id="wmo", placeholder="e.g., 744860", value="")
                    
                    # Target Years Row
                    with Horizontal(classes="input-row"):
                        with Vertical(classes="col"):
                            yield Label("Start Year", classes="input-label")
                            yield Input(id="start_year", placeholder="e.g., 1970", value="", type="integer")
                        with Vertical(classes="col"):
                            yield Label("End Year", classes="input-label")
                            yield Input(id="end_year", placeholder="e.g., 2024", value="", type="integer")
                    
                    # Target Temperatures Row
                    with Horizontal(classes="input-row"):
                        with Vertical(classes="col"):
                            yield Label("Winter Return Temp (°C)", classes="input-label")
                            yield Input(id="winter_temp", placeholder="e.g., 20.0", value="", type="number")
                        with Vertical(classes="col"):
                            yield Label("Summer Return Temp (°C)", classes="input-label")
                            yield Input(id="summer_temp", placeholder="e.g., 24.0", value="", type="number")
                    
                    # File Browser Row (Input Base TMY)
                    yield Label("Base TMY File to modify (.epw)", classes="input-label")
                    with Horizontal(classes="file-browse-row"):
                        yield Input(id="tmy_file", placeholder="Path to Base TMY File...", value="")
                        yield Button("Browse...", id="browse-button", variant="primary")

                    # File Browser Row (Output Save Path)
                    yield Label("Save Final Output EPW As", classes="input-label")
                    with Horizontal(classes="file-browse-row"):
                        yield Input(id="output_epw", placeholder="e.g., Output", value="")
                        yield Button("Browse...", id="browse-save-button", variant="primary")
                        
                    yield Button("Generate Weather Data", id="run-button", variant="success")
            
            with TabPane("2. Logs & Progress", id="tab-logs"):
                with Vertical():
                    yield ProgressBar(id="progress-bar", show_eta=True)
                    yield RichLog(id="log-view", markup=True)
                
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        
        # Handle the Input File Browse Button
        if event.button.id == "browse-button":
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True) 
            
            file_path = filedialog.askopenfilename(
                title="Select Base TMY File",
                filetypes=[("EPW Weather Files", "*.epw"), ("All Files", "*.*")]
            )
            root.destroy()
            
            if file_path:
                self.query_one("#tmy_file", Input).value = file_path
            return

        # Handle the Output File Save Browse Button
        if event.button.id == "browse-save-button":
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True) 
            
            file_path = filedialog.asksaveasfilename(
                title="Save Hybrid EPW File As",
                defaultextension=".epw",
                initialfile="Hybrid_Weather.epw",
                filetypes=[("EPW Weather Files", "*.epw"), ("All Files", "*.*")]
            )
            root.destroy()
            
            if file_path:
                self.query_one("#output_epw", Input).value = file_path
            return

        # Handle the Run Button
        if event.button.id == "run-button":
            wmo_str = self.query_one("#wmo", Input).value
            try:
                start_year = int(self.query_one("#start_year", Input).value)
                end_year = int(self.query_one("#end_year", Input).value)
                
                # Validation for Years
                if start_year < 1970:
                    self.query_one("#tabs", TabbedContent).active = "tab-logs"
                    self.query_one("#log-view", RichLog).write("[bold red]Error: Start Year must be 1970 or later. NOAA ISD data is not available before 1970.[/]")
                    return
                if start_year > end_year:
                    self.query_one("#tabs", TabbedContent).active = "tab-logs"
                    self.query_one("#log-view", RichLog).write("[bold red]Error: Start Year cannot be after End Year.[/]")
                    return

                wmo_list = [int(x.strip()) for x in wmo_str.split(",")]
                years = list(range(start_year, end_year + 1))
                winter_temp = float(self.query_one("#winter_temp", Input).value)
                summer_temp = float(self.query_one("#summer_temp", Input).value)
            except ValueError:
                self.query_one("#tabs", TabbedContent).active = "tab-logs"
                self.query_one("#log-view", RichLog).write("[bold red]Error: Ensure WMO, Years, and Temperatures are valid numbers.[/]")
                return

            tmy_file = self.query_one("#tmy_file", Input).value.strip()
            output_epw = self.query_one("#output_epw", Input).value.strip()

            if not tmy_file or not os.path.exists(tmy_file):
                self.query_one("#tabs", TabbedContent).active = "tab-logs"
                self.query_one("#log-view", RichLog).write(f"[bold red]Error: Base TMY file not found at '{tmy_file}'. Please provide a valid path.[/]")
                return

            self.query_one("#run-button", Button).disabled = True
            self.query_one("#tabs", TabbedContent).active = "tab-logs"
            self.set_timer(0.1, lambda: self.run_pipeline(wmo_list, years, winter_temp, summer_temp, tmy_file, output_epw))

    def show_modal(self, message: str):
        self.push_screen(ResultsModal(message))

    # =========================================================
    # Hybrid EPW Helper Methods
    # =========================================================
    def _get_epw_search_string(self, dt_obj, hour=1):
        return f",{dt_obj.month},{dt_obj.day},{hour},"

    def _get_week_data(self, epw_path, start_date):
        search_str = self._get_epw_search_string(start_date, hour=1)
        week_data = []
        capture = False
        
        if not os.path.exists(epw_path):
            raise FileNotFoundError(f"AMY file not found: {epw_path}")

        with open(epw_path, 'r') as f:
            lines = f.readlines()
            
        for line in lines:
            if not capture and search_str in line:
                capture = True
            if capture:
                week_data.append(line)
                if len(week_data) == 168:
                    break
        
        if not capture:
            raise ValueError(f"Date {start_date.strftime('%b %d')} not present in {epw_path}")
        if len(week_data) < 168:
            raise ValueError(f"Could not find a full week (168 hours) starting {start_date} in {epw_path}")
            
        return week_data

    @work(exclusive=True, thread=True)
    def run_pipeline(self, wmo_list, years, winter_temp, summer_temp, tmy_file, output_epw):
        
        log = self.query_one("#log-view", RichLog)
        progress_bar = self.query_one("#progress-bar", ProgressBar)

        def write_log(message):
            self.call_from_thread(log.write, message)

        write_log("\n[bold cyan]========================================[/]")
        write_log("[bold cyan] Starting Comprehensive EPW Pipeline...[/]")
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
                        
                        # Silence BOTH print statements AND the logging module
                        logging.disable(logging.CRITICAL) 
                        
                        with open(os.devnull, 'w') as fnull:
                            with redirect_stdout(fnull), redirect_stderr(fnull):
                                diyepw.create_amy_epw_files_for_years_and_wmos(
                                    [year], [wmo],
                                    max_records_to_interpolate=10,
                                    max_missing_amy_rows=300,
                                    allow_downloads=True,
                                    amy_epw_dir=temp_epw_dir
                                )
                                
                        logging.disable(logging.NOTSET) 
                                
                        write_log(f"[green]  -> Downloaded: WMO {wmo}, Year {year}[/]")
                    except Exception as e:
                        logging.disable(logging.NOTSET)
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
                "Global Horizontal Radiation {Wh/m2}", "SourceFile"
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
                "first of rolling max DBt", "first of rolling min DBt", "first of rolling max DPt", "first of rolling min DPt", 
                "first rolling avg date", "SourceFile"
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
                    first_vals["SourceFile"].append(row["SourceFile"])

            for col_name, val_list in first_vals.items():
                df[col_name] = pd.Series(val_list).reset_index(drop=True)

            # ---------------------------------------------------------
            # Step 4: Extract Return Temp Target Dates
            # ---------------------------------------------------------
            write_log("\n[bold yellow]--- Step 4: Extracting Target Dates ---[/]")
            
            valid_firsts = df.dropna(subset=["first rolling avg date"]).copy()
            modal_message = ""
            
            target_winter_date = None
            winter_amy_path = None
            target_summer_date = None
            summer_amy_path = None

            winter_mask = (valid_firsts["first of rolling min DBt"] >= winter_temp - 0.5) & \
                          (valid_firsts["first of rolling min DBt"] <= winter_temp + 0.5)
            winter_filtered = valid_firsts[winter_mask]
            
            if not winter_filtered.empty:
                winter_sorted = winter_filtered.sort_values(by="first of rolling avg GHR", ascending=True)
                target_winter_date = winter_sorted.iloc[0]["first rolling avg date"]
                source = winter_sorted.iloc[0]["SourceFile"]
                winter_amy_path = os.path.join(temp_epw_dir, source)
                
                w_msg = f"Winter Target Found: {target_winter_date.strftime('%Y-%m-%d')}\nMatches criteria: Min DBt ≈ {winter_temp}°C, Lowest GHR."
                write_log(f"[bold cyan]{w_msg}[/]")
                modal_message += f"[bold cyan]Winter Summary[/]\n{w_msg}\nSource: {source}\n\n"
            else:
                write_log(f"[bold red]No dates found matching Winter Return Temp {winter_temp}°C (±0.5).[/]")
                modal_message += f"[bold red]Winter Summary[/]\nNo dates found matching {winter_temp}°C.\n\n"

            summer_mask = (valid_firsts["first of rolling max DBt"] >= summer_temp - 0.5) & \
                          (valid_firsts["first of rolling max DBt"] <= summer_temp + 0.5)
            summer_filtered = valid_firsts[summer_mask]
            
            if not summer_filtered.empty:
                summer_sorted = summer_filtered.sort_values(by="first of rolling avg HI", ascending=False)
                target_summer_date = summer_sorted.iloc[0]["first rolling avg date"]
                source = summer_sorted.iloc[0]["SourceFile"]
                summer_amy_path = os.path.join(temp_epw_dir, source)
                
                s_msg = f"Summer Target Found: {target_summer_date.strftime('%Y-%m-%d')}\nMatches criteria: Max DBt ≈ {summer_temp}°C, Highest Heat Index."
                write_log(f"[bold red]{s_msg}[/]")
                modal_message += f"[bold yellow]Summer Summary[/]\n{s_msg}\nSource: {source}\n\n"
            else:
                write_log(f"[bold red]No dates found matching Summer Return Temp {summer_temp}°C (±0.5).[/]")
                modal_message += f"[bold red]Summer Summary[/]\nNo dates found matching {summer_temp}°C.\n\n"

            # ---------------------------------------------------------
            # Step 5: Generate Hybrid EPW
            # ---------------------------------------------------------
            if target_winter_date and target_summer_date:
                write_log("\n[bold yellow]--- Step 5: Constructing Hybrid EPW ---[/]")
                try:
                    events = [
                        {'date': target_winter_date, 'amy_file': winter_amy_path, 'name': 'Winter Period'},
                        {'date': target_summer_date, 'amy_file': summer_amy_path, 'name': 'Summer Period'}
                    ]
                    
                    # --- THE FIX: Sort strictly by calendar month and day, ignoring the historical year ---
                    events.sort(key=lambda x: (x['date'].month, x['date'].day))
                    # --------------------------------------------------------------------------------------

                    for event in events:
                        write_log(f"Extracting 168 hours for {event['name']}...")
                        event['data'] = self._get_week_data(event['amy_file'], event['date'])

                    with open(tmy_file, 'r') as f:
                        tmy_lines = f.readlines()

                    for event in events:
                        search_str = self._get_epw_search_string(event['date'], hour=1)
                        found = False
                        for idx, line in enumerate(tmy_lines):
                            if search_str in line:
                                event['start_index'] = idx
                                event['end_index'] = idx + 168
                                found = True
                                break
                        if not found:
                            raise ValueError(f"Date {event['date'].strftime('%b %d')} not present in TMY file.")

                    first_event, second_event = events[0], events[1]

                    if first_event['end_index'] > second_event['start_index']:
                        write_log("[bold red]Warning: The two selected weeks overlap. Merge may be corrupted.[/]")

                    new_content = []
                    new_content.extend(tmy_lines[ : first_event['start_index']])
                    new_content.extend(first_event['data'])
                    new_content.extend(tmy_lines[first_event['end_index'] : second_event['start_index']])
                    new_content.extend(second_event['data'])
                    new_content.extend(tmy_lines[second_event['end_index'] : ])

                    os.makedirs(os.path.dirname(os.path.abspath(output_epw)), exist_ok=True)
                    with open(output_epw, 'w') as f:
                        for line in new_content:
                            f.write(line)
                            
                    write_log(f"[bold green]Hybrid EPW successfully created at:\n{output_epw}[/]")
                    modal_message += f"[bold green]Hybrid EPW Export Location[/]\n{output_epw}"
                    
                except Exception as e:
                    write_log(f"[bold red]Error generating Hybrid EPW: {e}[/]")
                    modal_message += f"[bold red]Hybrid EPW Generation Failed[/]\n{e}"
            else:
                write_log("\n[bold red]--- Step 5 Skipped: Missing target dates to build Hybrid EPW ---[/]")

        # ---------------------------------------------------------
        # Finalization
        # ---------------------------------------------------------
        self.final_df = df
        
        self.call_from_thread(lambda: setattr(self.query_one("#run-button", Button), "disabled", False))
        self.call_from_thread(self.show_modal, modal_message)

if __name__ == "__main__":
    app = WeatherPipelineApp()
    app.run()
using GearDesign.Utility;
using Microsoft.Vbe.Interop;
using System;
using System.Data;
using System.DirectoryServices.ActiveDirectory;
using System.Drawing;
using System.Linq;
using System.Runtime.Versioning;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace GearDesign
{
    [SupportedOSPlatform("windows")]
    public partial class SimpleSizingForm : Form
    {
        private SimpleSizingInput _input;
        private SimpleSizingOutput _output;
        private DataTable _originalResults;
        private DataTable _filteredResults;
        private int _totalCombinations;
        private double _totalcalctime;
        private CancellationTokenSource _cancellationTokenSource;
        public SimpleSizingForm()
        {
            InitializeComponent();
            _input = new SimpleSizingInput();
            InitializeDefaultValues();
            SetupInputValidation();
            SetupDataGridView();
        }

        private void InitializeDefaultValues()
        {
            // Set default values
            txtTargetGR.Text = "3.0";
            txtTargetGRDev.Text = "5.0";
            txtZPinionMin.Text = "15";
            txtZPinionMax.Text = "30";
            txtZPinionStep.Text = "1";
            cmbHunting.SelectedIndex = 2; // No hunting
            txtMnMin.Text = "1.0";
            txtMnMax.Text = "3.0";
            txtMnStep.Text = "0.25";
            txtAMax.Text = "100.0";
            txtAMin.Text = "50.0";
            txtDMax.Text = "200.0";
            txtDMin.Text = "20.0";
            txtMaxCases.Text = "1000";
            txtHelixAngle.Text = "0.0";
            txtFaceWidth.Text = "10.0";
            txtPressureAngle.Text = "20.0";
            txtMinContactSF.Text = "1.2";
            txtMinBendingSF.Text = "1.6";
            chkEnableRating.Checked = false;
            // Initially disable rating controls
            txtMinContactSF.Enabled = false;
            txtMinBendingSF.Enabled = false;
            lblMinContactSF.Enabled = false;
            lblMinBendingSF.Enabled = false;
            cmbSortOption.SelectedIndex = 0; // All Results
            cmbFilterOption.SelectedIndex = 0; // Filtered Results
        }

        public void SetValues(SimpleSizingInput input)
        {
            _input = input;
            // Set UI controls based on input values
            txtTargetGR.Text = input.target_GR.ToString("F4");
            txtTargetGRDev.Text = (input.target_GR_dev * 100.0).ToString("F4");
            txtZPinionMin.Text = input.z_pinion_min.ToString("F0");
            txtZPinionMax.Text = input.z_pinion_max.ToString("F0");
            txtZPinionStep.Text = input.z_pinion_step.ToString("F0");
            cmbHunting.SelectedIndex = input.hunting;
            txtMnMin.Text = input.m_n_min.ToString("F4");
            txtMnMax.Text = input.m_n_max.ToString("F4");
            txtMnStep.Text = input.m_n_step.ToString("F4");
            txtAMax.Text = input.a_max.ToString("F4");
            txtAMin.Text = input.a_min.ToString("F4");
            txtDMax.Text = input.d_max.ToString("F4");
            txtDMin.Text = input.d_min.ToString("F4");
            txtMaxCases.Text = input.maxcases.ToString("F0");
            txtHelixAngle.Text = input.helix_angle.ToString("F4");
            txtFaceWidth.Text = input.face_width.ToString("F4");
            txtPressureAngle.Text = input.pressure_angle.ToString("F4");
            txtMinContactSF.Text = input.min_contact_safety_factor.ToString("F4");
            txtMinBendingSF.Text = input.min_bending_safety_factor.ToString("F4");
            // Note: chkEnableRating state is controlled by user, not from input
        }

        private async void BtnCalculate_Click(object sender, EventArgs e)
        {
            try
            {
                // Get input values
                _input.target_GR = double.Parse(txtTargetGR.Text);
                _input.target_GR_dev = double.Parse(txtTargetGRDev.Text) / 100.0;
                _input.z_pinion_min = Convert.ToInt32(txtZPinionMin.Text);
                _input.z_pinion_max = Convert.ToInt32(txtZPinionMax.Text);
                _input.z_pinion_step = Convert.ToInt32(txtZPinionStep.Text);
                _input.hunting = cmbHunting.SelectedIndex;
                _input.m_n_min = double.Parse(txtMnMin.Text);
                _input.m_n_max = double.Parse(txtMnMax.Text);
                _input.m_n_step = double.Parse(txtMnStep.Text);
                _input.a_max = double.Parse(txtAMax.Text);
                _input.a_min = double.Parse(txtAMin.Text);
                _input.d_max = double.Parse(txtDMax.Text);
                _input.d_min = double.Parse(txtDMin.Text);
                _input.maxcases = int.Parse(txtMaxCases.Text);
                _input.helix_angle = double.Parse(txtHelixAngle.Text); // Convert to radian;
                _input.face_width = double.Parse(txtFaceWidth.Text);
                _input.pressure_angle = double.Parse(txtPressureAngle.Text); // Convert to radian;
                _input.min_contact_safety_factor = double.Parse(txtMinContactSF.Text);
                _input.min_bending_safety_factor = double.Parse(txtMinBendingSF.Text);

                // Disable controls during calculation
                SetControlsEnabled(false);
                
                // Create cancellation token source
                _cancellationTokenSource = new CancellationTokenSource();
                
                // Show progress controls
                progressBar.Visible = true;
                lblProgress.Visible = true;
                btnStop.Visible = true;
                btnStop.Enabled = true;
                progressBar.Value = 0;
                lblProgress.Text = "Calculating...";
                
                // Force UI update
                this.Refresh();
                
                // Calculate - use checkbox to determine rating setting
                bool withRating = chkEnableRating.Checked;
                
                // Run calculation in background thread with cancellation support
                bool useParallel = withRating; // Use parallel processing when rating is enabled
                _output = await SimpleSizing.Calculate(_input, withRating, false, UpdateProgress, _cancellationTokenSource.Token);

                // Check if cancelled after calculation
                if (_cancellationTokenSource.Token.IsCancellationRequested)
                {
                    System.Diagnostics.Debug.WriteLine("Calculation was cancelled - skipping result processing");
                    MessageBox.Show("Calculation was cancelled by user.", "Calculation Cancelled", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    lblProgress.Text = "Cancelled";
                    
                    // Clear any partial results
                    _output = null;
                    dgvResults.DataSource = null;
                }
                else
                {
                    // Store original results  
                    _originalResults = _output.GearList.Copy();
                    _filteredResults = _output.FilteredResults.Copy();
                    _totalCombinations = _output.totalcases;
                    _totalcalctime = _output.CalcTime;

                    // Display results
                    ApplySortOption();
                    lblProgress.Text = "Ready";
                }
                
                // Hide progress controls
                progressBar.Visible = false;
                lblProgress.Visible = false;
                btnStop.Visible = false;
            }
            catch (Exception ex)
            {
                // Debug logging for exception analysis
                System.Diagnostics.Debug.WriteLine($"Exception caught: {ex.GetType().Name} - {ex.Message}");
                                
                // Hide progress controls on error or cancellation
                progressBar.Visible = false;
                lblProgress.Visible = false;
                btnStop.Visible = false;
            }
            finally
            {
                // Re-enable controls and cleanup
                SetControlsEnabled(true);
                _cancellationTokenSource?.Dispose();
                _cancellationTokenSource = null;
            }
        }

        private void BtnExportCSV_Click(object sender, EventArgs e)
        {
            if (_output?.GearList != null && _output.GearList.Rows.Count > 0)
            {
                ExtensionMethods.GetCSVfromDGV(dgvResults);
            }
            else
            {
                MessageBox.Show("No data to export. Please calculate first.", "Export Error", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        private void BtnCopyToClipboard_Click(object sender, EventArgs e)
        {
            if (_output?.GearList != null && _output.GearList.Rows.Count > 0)
            {
                ExtensionMethods.CopyDataTableToClipboard(_output.GearList);
            }
            else
            {
                MessageBox.Show("No data to copy. Please calculate first.", "Copy Error", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        private void BtnReset_Click(object sender, EventArgs e)
        {
            SetValues(_input);
            dgvResults.DataSource = null;
            lblResultCount.Text = "Showing: 0 / Total Combinations: 0";
            _originalResults = null;
            _filteredResults = null;
            _totalCombinations = 0;
            _totalcalctime = 0.0;
        }

        private void SetupInputValidation()
        {
            // Double type TextBoxes - allow up to 4 decimal places
            TextBox[] doubleTextBoxes = {
                txtTargetGR, txtTargetGRDev, txtMnMin, txtMnMax, txtMnStep,
                txtAMin, txtAMax, txtDMin, txtDMax, txtHelixAngle, txtFaceWidth, txtPressureAngle,
                txtMinContactSF, txtMinBendingSF
            };

            foreach (var textBox in doubleTextBoxes)
            {
                textBox.KeyPress += DoubleTextBox_KeyPress;
                textBox.Leave += DoubleTextBox_Leave;
            }

            // Integer type TextBoxes - allow only positive integers
            TextBox[] intTextBoxes = {
                txtZPinionMin, txtZPinionMax, txtZPinionStep, txtMaxCases
            };

            foreach (var textBox in intTextBoxes)
            {
                textBox.KeyPress += IntTextBox_KeyPress;
                textBox.Leave += IntTextBox_Leave;
            }
        }

        private void DoubleTextBox_KeyPress(object sender, KeyPressEventArgs e)
        {
            TextBox textBox = sender as TextBox;
            
            // Allow control keys (backspace, delete, etc.)
            if (char.IsControl(e.KeyChar))
                return;

            // Allow digits
            if (char.IsDigit(e.KeyChar))
                return;

            // Allow decimal point only if not already present
            if (e.KeyChar == '.' && !textBox.Text.Contains('.'))
                return;

            // Block all other characters
            e.Handled = true;
        }

        private void DoubleTextBox_Leave(object sender, EventArgs e)
        {
            TextBox textBox = sender as TextBox;
            
            if (double.TryParse(textBox.Text, out double value))
            {
                // Round to 4 decimal places
                textBox.Text = Math.Round(value, 4).ToString("F4");
            }
            else if (!string.IsNullOrEmpty(textBox.Text))
            {
                // Invalid input - reset to 0
                textBox.Text = "0.0000";
            }
        }

        private void IntTextBox_KeyPress(object sender, KeyPressEventArgs e)
        {
            // Allow control keys (backspace, delete, etc.)
            if (char.IsControl(e.KeyChar))
                return;

            // Allow only digits
            if (char.IsDigit(e.KeyChar))
                return;

            // Block all other characters
            e.Handled = true;
        }

        private void IntTextBox_Leave(object sender, EventArgs e)
        {
            TextBox textBox = sender as TextBox;
            
            if (int.TryParse(textBox.Text, out int value))
            {
                // Ensure positive integer
                if (value <= 0)
                {
                    textBox.Text = "1";
                }
            }
            else if (!string.IsNullOrEmpty(textBox.Text))
            {
                // Invalid input - reset to 1
                textBox.Text = "1";
            }
        }

        private void CmbSortOption_SelectedIndexChanged(object sender, EventArgs e)
        {
            if (_originalResults != null)
            {
                ApplySortOption();
            }
        }

        private void CmbFilterOption_SelectedIndexChanged(object sender, EventArgs e)
        {
            if (_originalResults != null)
            {
                ApplySortOption();
            }
        }

        private void ApplySortOption()
        {
            if (_originalResults == null || _filteredResults == null) return;

            // First, determine which dataset to use based on filter option
            DataTable baseResults;
            switch (cmbFilterOption.SelectedIndex)
            {
                case 0: // Filtered Results
                    baseResults = _filteredResults.Copy();
                    break;
                case 1: // All Results
                    baseResults = _originalResults.Copy();
                    break;
                default:
                    baseResults = _filteredResults.Copy();
                    break;
            }

            // Then apply sorting
            DataTable sortedResults;
            switch (cmbSortOption.SelectedIndex)
            {
                case 0: // No sorting (original order)
                    sortedResults = baseResults;
                    break;
                case 1: // Sort by Gear Ratio
                    sortedResults = SortDataTable(baseResults, "GearRatio", "ASC");
                    break;
                case 2: // Sort by Center Distance
                    sortedResults = SortDataTable(baseResults, "a [mm]", "ASC");
                    break;
                case 3: // Sort by Module
                    sortedResults = SortDataTable(baseResults, "m_n [mm]", "ASC");
                    break;
                default:
                    sortedResults = baseResults;
                    break;
            }

            // Update DataGridView
            dgvResults.DataSource = sortedResults;
            ExtensionMethods.SetDGV(dgvResults, "F3");
            ExtensionMethods.SetRowNumber(dgvResults);
            dgvResults.Columns["z1"].DefaultCellStyle.Format = "F0";
            dgvResults.Columns["z2"].DefaultCellStyle.Format = "F0";
            if (dgvResults.Columns.Contains("Rank"))
            {
                dgvResults.Columns["Rank"].DefaultCellStyle.Format = "F0";
            }
            // Update result count display
            string filterStatus = cmbFilterOption.SelectedIndex == 0 ? "Filtered" : "All";
            string countInfo = $"Showing: {sortedResults.Rows.Count} ({filterStatus}) / Total Combinations: {_totalCombinations} / Total calculation time: {_totalcalctime:F3} sec";
            lblResultCount.Text = countInfo;

            // Update output reference for export functions
            _output.GearList = sortedResults;
        }

        private DataTable SortDataTable(DataTable dataTable, string columnName, string direction)
        {
            DataTable sortedTable = dataTable.Copy();
            DataView dataView = sortedTable.DefaultView;
            dataView.Sort = columnName + " " + direction;
            return dataView.ToTable();
        }

        private void ChkEnableRating_CheckedChanged(object sender, EventArgs e)
        {
            // Enable/disable rating input controls based on checkbox state
            bool isEnabled = chkEnableRating.Checked;
            txtMinContactSF.Enabled = isEnabled;
            txtMinBendingSF.Enabled = isEnabled;
            lblMinContactSF.Enabled = isEnabled;
            lblMinBendingSF.Enabled = isEnabled;
        }

        private void BtnStop_Click(object sender, EventArgs e)
        {
            try
            {
                // Request cancellation using boolean flag (same as Sizing_GearPair)
                _cancellationTokenSource?.Cancel();
                
                // Update UI to show cancelling status
                lblProgress.Text = "Cancelling...";
                btnStop.Enabled = false;
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error stopping calculation: {ex.Message}", "Stop Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void SetControlsEnabled(bool enabled)
        {
            // Enable/disable input controls during calculation
            groupBoxInput.Enabled = enabled;
            btnCalculate.Enabled = enabled;
            btnReset.Enabled = enabled;
            
            // Stop button is only enabled and visible during calculation
            btnStop.Enabled = !enabled;
            btnStop.Visible = !enabled;
            
            // Keep export buttons disabled if no data
            if (enabled && _output?.GearList != null && _output.GearList.Rows.Count > 0)
            {
                btnExportCSV.Enabled = true;
                btnCopyToClipboard.Enabled = true;
            }
            else if (!enabled)
            {
                btnExportCSV.Enabled = false;
                btnCopyToClipboard.Enabled = false;
            }
        }

        private void UpdateProgress(int current, int total)
        {
            // Skip progress updates if cancelled
            if (_cancellationTokenSource.Token.IsCancellationRequested) return;
            
            // This method is called from background thread, so we need to invoke on UI thread
            if (InvokeRequired)
            {
                if (!_cancellationTokenSource.Token.IsCancellationRequested)
                {
                    Invoke(new Action<int, int>(UpdateProgress), current, total);
                }
                return;
            }

            // Update progress bar and label
            if (total > 0 && !_cancellationTokenSource.Token.IsCancellationRequested)
            {
                try
                {
                    int percentage = (int)((double)current / total * 100);
                    progressBar.Value = Math.Min(percentage, 100);
                    lblProgress.Text = $"{current}/{total} ({percentage}%)";
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"Progress update error: {ex.Message}");
                }
            }
        }

        private void SetupDataGridView()
        {
            // Setup DataGridView row header double-click event
            dgvResults.RowHeaderMouseDoubleClick += DgvResults_RowHeaderMouseDoubleClick;
        }

        private void DgvResults_RowHeaderMouseDoubleClick(object sender, DataGridViewCellMouseEventArgs e)
        {
            try
            {
                DataGridView dgv = sender as DataGridView;
                int rowIndex = e.RowIndex;

                if (rowIndex < 0 || dgv.Rows.Count <= rowIndex)
                    return;

                if (_input.mainForm == null)
                {
                    MessageBox.Show("Main form reference not found. Cannot apply values.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }

                DataGridViewRow selectedRow = dgv.Rows[rowIndex];

                // Extract values from the selected row
                string z1 = GetCellValueSafely(selectedRow, "z1");
                string z2 = GetCellValueSafely(selectedRow, "z2"); 
                string module = GetCellValueSafely(selectedRow, "m_n [mm]");
                string a = GetCellValueSafely(selectedRow, "a [mm]");
                string helixAngle = GetCellValueSafely(selectedRow, "ет [deg]");
                string pressureAngle = GetCellValueSafely(selectedRow, "ес_n [deg]");
                string faceWidth = GetCellValueSafely(selectedRow, "Facewidth [mm]");

                // Apply values to main form
                if (!string.IsNullOrEmpty(z1) && !string.IsNullOrEmpty(z2) && !string.IsNullOrEmpty(module))
                {
                    _input.mainForm.TB_m_n.Text = module;
                    _input.mainForm.TB_z1.Text = z1;
                    _input.mainForm.TB_z2.Text = z2;
                    _input.mainForm.TB_x1.Text = "0.0000";
                    _input.mainForm.TB_x2.Text = "0.0000";                    
                    _input.mainForm.TB_a1.Text = a;
                    _input.mainForm.TB_j_bn1.Text = "0.0000";
                    _input.mainForm.TB_alpha_n.Text = pressureAngle;
                    _input.mainForm.TB_beta.Text = helixAngle;
                    _input.mainForm.TB_b1.Text = faceWidth;
                    _input.mainForm.TB_b2.Text = faceWidth;
                    _input.mainForm.Drop_CDMethod.SelectedIndex = 0; // Center Distance Method

                    MessageBox.Show($"Values applied to main form:\nZ1: {z1}\nZ2: {z2}\nModule: {module} mm", "Values Applied", MessageBoxButtons.OK, MessageBoxIcon.Information);
                }
                else
                {
                    MessageBox.Show("Unable to extract required values (z1, z2, module) from the selected row.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error applying values to main form: {ex.Message}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private bool IsCancellationException(Exception ex)
        {
            // Check if the exception or any inner exception is a cancellation
            var currentException = ex;
            while (currentException != null)
            {
                if (currentException is OperationCanceledException || 
                    currentException is TaskCanceledException)
                {
                    return true;
                }
                
                // Also check for AggregateException which might contain cancellation
                if (currentException is AggregateException aggEx)
                {
                    foreach (var innerEx in aggEx.InnerExceptions)
                    {
                        if (IsCancellationException(innerEx))
                            return true;
                    }
                }
                
                currentException = currentException.InnerException;
            }
            return false;
        }

        private string GetCellValueSafely(DataGridViewRow row, string columnName)
        {
            try
            {
                if (row.DataGridView.Columns.Contains(columnName) && row.Cells[columnName].Value != null)
                {
                    return row.Cells[columnName].Value.ToString();
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error getting cell value for {columnName}: {ex.Message}");
            }
            return string.Empty;
        }
    }
}
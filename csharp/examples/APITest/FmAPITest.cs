using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Windows.Forms;
using System.IO.Ports;
using JX1000;
using System.IO;

namespace APITest
{
    public partial class FmAPITest : Form
    {
        JX1000_API jxapi = new JX1000_API();

        public FmAPITest()
        {
            InitializeComponent();
        }

        // Automatically get available COM ports
        public static string[] GetPorts()
        {
            List<string> port = new List<string>();

            // Detect usable COM ports
            foreach (string serialport in SerialPort.GetPortNames()) {
                try {
                    SerialPort serial = new SerialPort(serialport);
                    serial.Open();
                    serial.Close();
                    port.Add(serialport);
                } catch {
                    continue;
                }
            }

            if (port.Count > 0)
                return port.ToArray();

            return null;
        }

        private void bt_refresh_Click(object sender, EventArgs e)
        {
            cb_port.Text = "";
            cb_port.Items.Clear();

            string[] ports = GetPorts();
            if (ports != null && ports.Length > 0) {
                cb_port.Items.AddRange(ports);
                cb_port.SelectedIndex = 0;
            }
        }

        private void bt_port_Click(object sender, EventArgs e)
        {
            if (jxapi.PortIsOpen()) {
                jxapi.ClosePort();
            } else {
                jxapi.OpenPort(cb_port.Text);
            }
        }

        private void FmAPITest_Load(object sender, EventArgs e)
        {
            jxapi.RcvDealHandler += new JX1000_API.RcvDealDelegate(dealDataHandler);
        }

        private void Log(string str)
        {
            tb_log.AppendText(str + "\r\n");
        }

        private void LogData(string str)
        {
            tb_data.AppendText(str + "\r\n");
        }

        private void dealDataHandler(EVENT_CODE code, string value)
        {
            this.BeginInvoke(new Action(() =>
            {
                switch (code)
                {
                    // Port events
                    case EVENT_CODE.PortOpen:
                        bt_port.Text = "Close";
                        Log(value);
                        break;

                    case EVENT_CODE.PortClose:
                        bt_port.Text = "Connect";
                        Log(value);
                        break;

                    case EVENT_CODE.PortError:
                        Log(value);
                        break;

                    // Tester connection
                    case EVENT_CODE.TesterConnSuc:
                        Log(value);
                        break;

                    case EVENT_CODE.TesterData:
                        LogData(value);
                        break;

                    // Download rule file
                    case EVENT_CODE.TesterDownload:
                        LogData("Download: " + value);
                        break;

                    case EVENT_CODE.TesterDownloadPro:
                        LogData("Progress: " + value);
                        break;
                }

            }));
        }

        private void button1_Click(object sender, EventArgs e)
        {
            tb_data.Clear();
            jxapi.TestStart();
        }

        private void button2_Click(object sender, EventArgs e)
        {
            jxapi.TestStop();
        }

        private void button3_Click(object sender, EventArgs e)
        {
            OpenFileDialog dlg = new OpenFileDialog();
            dlg.Filter = "Bin files (*.jx1000)|*.jx1000";
            dlg.Multiselect = false;

            if (dlg.ShowDialog() == DialogResult.OK) {
                string strFile = dlg.FileName;

                FileStream fs = new FileStream(strFile, FileMode.Open, FileAccess.Read);
                BinaryReader br = new BinaryReader(fs);

                int len = (int)fs.Length;
                byte[] buf = br.ReadBytes(len);

                br.Close();
                fs.Close();

                jxapi.DownloadRules(buf);
            }
        }

        // Read from board
        private void button4_Click(object sender, EventArgs e)
        {
            try {
                int com_index, ch_index, memory_addr;
                float data;

                com_index = Convert.ToByte(textBox1.Text);
                ch_index = Convert.ToByte(textBox2.Text);
                memory_addr = Convert.ToUInt16(textBox3.Text);

                /*
                 * Read board memory:
                 *  ComIndex     Interface board number (>=1)
                 *  ChIndex      Channel index on the board (1–8)
                 *  MemoryAddr   Memory address to read
                 *  overtime     Timeout waiting for response
                 *  Data         Returned value
                 * 
                 * Return codes:
                 *  -1 Program exception
                 *  -2 Send failure
                 *  -3 Timeout
                 *   0 Success
                 *   1 Parameter error
                 *   2 Tester not connected to board
                 *   3 No board exists at the specified location
                 *   4 Read data error
                 */
                int ret = jxapi.DevRead(com_index, ch_index, memory_addr, 100, out data);

                LogData(string.Format("Board Read, Status[{0}], Value[{1}]", ret, data));
            }
            catch {
                MessageBox.Show("Invalid parameter input!");
            }
        }

        // Write to board
        private void button5_Click(object sender, EventArgs e)
        {
            try {
                int com_index, ch_index, memory_addr;
                decimal data;

                com_index = Convert.ToByte(textBox4.Text);
                ch_index = Convert.ToByte(textBox5.Text);
                memory_addr = Convert.ToUInt16(textBox6.Text);
                data = Convert.ToDecimal(textBox7.Text);

                /*
                 * Write to board memory:
                 *  ComIndex     Interface board number (>=1)
                 *  ChIndex      Channel index (1–8)
                 *  MemoryAddr   Memory address to write
                 *  Data         Data to write
                 * 
                 * Return codes:
                 *  -1 Program exception
                 *  -2 Send failure
                 *  -3 Timeout
                 *   0 Success
                 *   1 Parameter error
                 *   2 Tester not connected to board
                 *   3 No board exists at the specified location
                 *   4 Write data error
                 *   5 Write data verification error
                 */
                int ret = jxapi.DevWrite(com_index, ch_index, memory_addr, (float)data);

                LogData(string.Format("Board Write, Status[{0}], Value[{1}]", ret, data));
            }
            catch {
                MessageBox.Show("Invalid parameter input!");
            }
        }
    }
}

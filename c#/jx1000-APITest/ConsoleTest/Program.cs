using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using JX1000;
using System.Threading;

namespace ConsoleTest
{
    class Program
    {
        private static int Step = 0, Overtime = 0;
        private static bool IsStart = false, IsEnd = false;
        static JX1000_API jxapi = new JX1000_API();

        static void Log(string str)
        {
            Console.WriteLine("System: " + str);
        }

        static void Main(string[] args)
        {
            // Validate arguments
            if (args == null) {
                Log("Parameter error – no arguments");
                goto EXEC_END;
            }

            if (args.Length != 1) {
                Log("Parameter error – incorrect number of arguments");
                goto EXEC_END;
            }

            try {
                if (args[0].Substring(0, 3).ToUpper() != "COM") {
                    Log("Parameter error – invalid port number");
                    goto EXEC_END;
                }
            } catch {
                Log("Parameter error – invalid port number");
                goto EXEC_END;
            }

            jxapi.RcvDealHandler += new JX1000_API.RcvDealDelegate(dealDataHandler);

            Step = 0;
            Overtime = 0;

            // Open communication port
            if (jxapi.OpenPort(args[0])) {
                while (true) {
                    Thread.Sleep(10);

                    if (Step == 4) { // Device connected
                        break;
                    } else if (Step == 2) { // Port closed
                        goto EXEC_END;
                    } else if (Step == 3) { // Port error
                        goto EXEC_END;
                    }

                    if (++Overtime > 100) {
                        Log("Error – device not recognized");
                        goto EXEC_END;
                    }
                }
            } else {
                Log("Parameter error – failed to open port");
                goto EXEC_END;
            }

            // Begin test
            if (!jxapi.TestStart()) {
                goto EXEC_END;
            }

            Step = 0;
            Overtime = 0;
            IsStart = false;
            IsEnd = false;

            // Wait for test data
            while (true) {
                Thread.Sleep(10);

                if (IsEnd)
                    break;

                if (Step == 3 || Step == 2)
                    break;

                if (!IsStart) {
                    if (++Overtime > 200) {
                        Log("Error – data reception timeout");
                        goto EXEC_END;
                    }
                }
            }

        EXEC_END:
            jxapi.ClosePort();
        }

        private static void dealDataHandler(EVENT_CODE code, string value)
        {
            switch (code) {
                case EVENT_CODE.PortOpen:
                    Log(value);
                    Step = 1;
                    break;

                case EVENT_CODE.PortClose:
                    Log(value);
                    Step = 2;
                    break;

                case EVENT_CODE.PortError:
                    Log(value);
                    Step = 3;
                    break;

                case EVENT_CODE.TesterConnSuc:
                    Step = 4;
                    Log(value);
                    break;

                case EVENT_CODE.TesterData:
                    Console.WriteLine(value);

                    // Remove surrounding { }
                    string raw_str = value.Substring(1, value.Length - 2);
                    string[] raw_buf = raw_str.Split(',');

                    if (raw_buf.Length < 2)
                        return;

                    // Detect start
                    if (raw_buf[0] == "ST") {
                        IsStart = true;
                    }

                    // Detect end
                    if (raw_buf[0] == "ED") {
                        IsEnd = true;
                    }
                    break;
            }
        }

    }
}

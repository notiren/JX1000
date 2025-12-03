using System;
using System.Collections.Generic;
using System.IO.Ports;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

namespace JX1000;

public class JX1000_API
{
	private struct TRULE_DOWN
	{
		public byte State;

		public ushort Addr;

		public byte Len;

		public byte[] CmdBuf;
	}

	[StructLayout(LayoutKind.Sequential, Pack = 1)]
	private struct TINFOR
	{
		public byte HardType;

		public byte Version;

		public byte ComNumber;

		public byte ModelNumber;

		public ushort CmdBytes;
	}

	private struct DEV_REQUEST
	{
		public byte ComIndex;

		public byte ChIndex;

		public ushort MemoryAddr;

		public float Data;
	}

	[StructLayout(LayoutKind.Sequential, Pack = 1)]
	private struct DEV_RETURN
	{
		public byte ComIndex;

		public byte ChIndex;

		public byte Result;

		public ushort MemoryAddr;

		public float Data;
	}

	private enum ERuleDown
	{
		Idle,
		Suc,
		Err
	}

	public delegate void RcvDealDelegate(EVENT_CODE code, string value);

	private const byte FrameHeadH = 165;

	private const byte FrameHeadL = 94;

	public RcvDealDelegate RcvDealHandler;

	private bool SerialIsOpen = false;

	private bool IsInitEnd = false;

	private SerialPort serial = new SerialPort();

	private List<byte> rcvDataList = new List<byte>();

	private bool IsGetInfor = false;

	private ERuleDown RuleDownFlag = ERuleDown.Idle;

	private bool IsReadOK = false;

	private DEV_RETURN ReadRet = default(DEV_RETURN);

	private bool IsWriteOK = false;

	private DEV_RETURN WriteRet = default(DEV_RETURN);

	private TRcvData rcvData = default(TRcvData);

	private bool isDownloadStart = false;

	private byte checkSum(byte[] arr_buff, int len)
	{
		int num = 0;
		for (int i = 0; i < len; i++)
		{
			num += arr_buff[i];
		}
		return (byte)(num & 0xFF);
	}

	private bool frameGroup(EFRAME cmd, byte[] data, int data_len)
	{
		byte[] array = new byte[data_len + 5];
		array[0] = 165;
		array[1] = 94;
		array[2] = (byte)data_len;
		array[3] = (byte)cmd;
		Array.Copy(data, 0, array, 4, data_len);
		array[data_len + 4] = checkSum(array, data_len + 4);
		return SendBytes(array);
	}

	private bool GetCmd(EFRAME cmd)
	{
		byte[] data = new byte[2];
		return frameGroup(cmd, data, 2);
	}

	private bool Debug(string val)
	{
		byte[] bytes = Encoding.ASCII.GetBytes(val);
		return frameGroup(EFRAME.LOG, bytes, bytes.Length);
	}

	private unsafe object Bytes2Struct(byte[] bytes, Type type)
	{
		fixed (byte* value = &bytes[0])
		{
			return Marshal.PtrToStructure(new IntPtr(value), type);
		}
	}

	private bool dataDeal(byte[] frame, int len, ref TRcvData rcv_data)
	{
		int num = frame[2];
		byte[] array = new byte[num];
		Array.Copy(frame, 4, array, 0, num);
		rcv_data.Cmd = (EFRAME)frame[3];
		switch (rcv_data.Cmd)
		{
		case EFRAME.Infor:
		{
			TINFOR tINFOR = default(TINFOR);
			tINFOR = (TINFOR)Bytes2Struct(array, typeof(TINFOR));
			rcv_data.Res = string.Format("类型[{0}],版本[{1}],接口板[{2}],板卡数[{3}]", tINFOR.HardType, ((double)(int)tINFOR.Version * 1.0 / 10.0).ToString("#0.0"), tINFOR.ComNumber, tINFOR.ModelNumber);
			IsGetInfor = false;
			break;
		}
		case EFRAME.RuleDown:
			if (array[0] == 1)
			{
				RuleDownFlag = ERuleDown.Suc;
			}
			else if (array[0] == 2)
			{
				RuleDownFlag = ERuleDown.Err;
			}
			break;
		case EFRAME.DevRead:
			ReadRet = (DEV_RETURN)Bytes2Struct(array, typeof(DEV_RETURN));
			IsReadOK = true;
			break;
		case EFRAME.DevWrite:
			WriteRet = (DEV_RETURN)Bytes2Struct(array, typeof(DEV_RETURN));
			IsWriteOK = true;
			break;
		case EFRAME.RES:
			rcv_data.Res = Encoding.Default.GetString(array);
			break;
		case EFRAME.LOG:
			rcv_data.Res = Encoding.Default.GetString(array);
			break;
		}
		return true;
	}

	private bool RcvDataDeal(ref TRcvData res, byte[] raw, int len)
	{
		res.State = false;
		if (len > 0)
		{
			rcvDataList.AddRange(raw);
		}
		if (rcvDataList.Count < 7)
		{
			return false;
		}
		do
		{
			if (rcvDataList[0] == 165 && rcvDataList[1] == 94)
			{
				int num = rcvDataList[2];
				if (num + 5 > rcvDataList.Count)
				{
					break;
				}
				byte[] array = new byte[num + 5];
				Array.Copy(rcvDataList.ToArray(), 0, array, 0, num + 5);
				if (checkSum(array, num + 4) == array[num + 4])
				{
					dataDeal(array, num + 5, ref res);
					rcvDataList.RemoveRange(0, num + 5);
					res.State = true;
					return true;
				}
				rcvDataList.RemoveRange(0, 2);
			}
			else
			{
				rcvDataList.RemoveAt(0);
			}
		}
		while (rcvDataList.Count >= 7);
		return false;
	}

	private void dealDataHandler(EVENT_CODE code, string value)
	{
		if (RcvDealHandler != null)
		{
			RcvDealHandler(code, value);
		}
	}

	private void Init()
	{
		serial.Parity = Parity.None;
		serial.StopBits = StopBits.One;
		serial.DataBits = 8;
		serial.ReadBufferSize = 2048;
		serial.ReadTimeout = 100;
		serial.DataReceived += serial_DataReceived;
	}

	public bool OpenPort(string port)
	{
		if (!IsInitEnd)
		{
			IsInitEnd = true;
			Init();
		}
		if (serial.IsOpen)
		{
			dealDataHandler(EVENT_CODE.PortError, "端口已打开");
			SerialIsOpen = false;
			return false;
		}
		serial.PortName = port;
		serial.BaudRate = 115200;
		try
		{
			serial.Open();
			SerialIsOpen = true;
			dealDataHandler(EVENT_CODE.PortOpen, "打开端口成功");
			GetCmd(EFRAME.Infor);
		}
		catch
		{
			dealDataHandler(EVENT_CODE.PortError, "打开端口失败");
			SerialIsOpen = false;
		}
		return SerialIsOpen;
	}

	public void ClosePort()
	{
		dealDataHandler(EVENT_CODE.PortClose, "关闭端口");
		SerialIsOpen = false;
		if (serial.IsOpen)
		{
			serial.Close();
		}
	}

	private void serial_DataReceived(object sender, SerialDataReceivedEventArgs e)
	{
		try
		{
			int bytesToRead = serial.BytesToRead;
			byte[] array = new byte[bytesToRead];
			if (bytesToRead > 0)
			{
				bytesToRead = serial.Read(array, 0, bytesToRead);
				rcvDataAnalysis(array);
			}
		}
		catch
		{
			throw;
		}
	}

	private void rcvDataAnalysis(byte[] rcv_data)
	{
		bool flag = false;
		int len = rcv_data.Length;
		do
		{
			flag = RcvDataDeal(ref rcvData, rcv_data, len);
			len = 0;
			if (rcvData.State)
			{
				switch (rcvData.Cmd)
				{
				case EFRAME.Infor:
					dealDataHandler(EVENT_CODE.TesterConnSuc, rcvData.Res);
					break;
				case EFRAME.RES:
					dealDataHandler(EVENT_CODE.TesterData, rcvData.Res);
					break;
				}
			}
		}
		while (flag);
	}

	private bool SendBytes(byte[] send_buf)
	{
		if (!serial.IsOpen)
		{
			dealDataHandler(EVENT_CODE.PortError, "端口未打开");
			return false;
		}
		try
		{
			serial.Write(send_buf, 0, send_buf.Length);
		}
		catch
		{
			ClosePort();
			return false;
		}
		return true;
	}

	private bool RuleDown(TRULE_DOWN down)
	{
		CBuf cBuf = new CBuf();
		cBuf.Write(down.State);
		cBuf.Write(down.Addr);
		cBuf.Write(down.Len);
		cBuf.Write(down.CmdBuf);
		byte[] array = cBuf.ToBytes();
		return frameGroup(EFRAME.RuleDown, array, array.Length);
	}

	public int DevRead(int ComIndex, int ChIndex, int MemoryAddr, int overtime, out float Data)
	{
		Data = 0f;
		try
		{
			CBuf cBuf = new CBuf();
			DEV_REQUEST dEV_REQUEST = new DEV_REQUEST
			{
				ComIndex = (byte)ComIndex,
				ChIndex = (byte)ChIndex,
				MemoryAddr = (ushort)MemoryAddr,
				Data = 0f
			};
			cBuf.Write(dEV_REQUEST.ComIndex);
			cBuf.Write(dEV_REQUEST.ChIndex);
			cBuf.Write(dEV_REQUEST.MemoryAddr);
			cBuf.Write(dEV_REQUEST.Data);
			byte[] array = cBuf.ToBytes();
			IsReadOK = false;
			if (!frameGroup(EFRAME.DevRead, array, array.Length))
			{
				return -2;
			}
			int num = 0;
			while (!IsReadOK)
			{
				Thread.Sleep(1);
				if (++num >= overtime)
				{
					return -3;
				}
			}
			Data = ReadRet.Data;
			return ReadRet.Result;
		}
		catch
		{
			return -1;
		}
	}

	public int DevWrite(int ComIndex, int ChIndex, int MemoryAddr, float Data)
	{
		try
		{
			CBuf cBuf = new CBuf();
			DEV_REQUEST dEV_REQUEST = new DEV_REQUEST
			{
				ComIndex = (byte)ComIndex,
				ChIndex = (byte)ChIndex,
				MemoryAddr = (ushort)MemoryAddr,
				Data = Data
			};
			cBuf.Write(dEV_REQUEST.ComIndex);
			cBuf.Write(dEV_REQUEST.ChIndex);
			cBuf.Write(dEV_REQUEST.MemoryAddr);
			cBuf.Write(dEV_REQUEST.Data);
			byte[] array = cBuf.ToBytes();
			IsWriteOK = false;
			if (!frameGroup(EFRAME.DevWrite, array, array.Length))
			{
				return -2;
			}
			int num = 0;
			while (!IsWriteOK)
			{
				Thread.Sleep(1);
				if (++num >= 50)
				{
					return -3;
				}
			}
			return WriteRet.Result;
		}
		catch
		{
			return -1;
		}
	}

	public bool TestStart()
	{
		return Debug("cmd_EnableExec()\r\n");
	}

	public bool TestStop()
	{
		return Debug("cmd_ExitExec()\r\n");
	}

	public bool PortIsOpen()
	{
		return SerialIsOpen;
	}

	public void DownloadRules(byte[] buf)
	{
		if (!SerialIsOpen)
		{
			dealDataHandler(EVENT_CODE.TesterDownload, "端口未连接");
			isDownloadStart = false;
			return;
		}
		if (isDownloadStart)
		{
			dealDataHandler(EVENT_CODE.TesterDownload, "正在下载中");
			return;
		}
		if (buf == null)
		{
			dealDataHandler(EVENT_CODE.TesterDownload, "数据为空");
			return;
		}
		if (buf.Length < 10)
		{
			dealDataHandler(EVENT_CODE.TesterDownload, "数据错误1");
			return;
		}
		if (buf[0] != 35 || buf[7] != 42)
		{
			dealDataHandler(EVENT_CODE.TesterDownload, "数据错误2");
			return;
		}
		new Thread((ThreadStart)delegate
		{
			IsGetInfor = true;
			if (!GetCmd(EFRAME.Infor))
			{
				IsGetInfor = false;
				dealDataHandler(EVENT_CODE.TesterDownload, "执行失败, 查询设备");
			}
			else
			{
				int num = 300;
				while (true)
				{
					if (!IsGetInfor)
					{
						isDownloadStart = true;
						int num2 = 0;
						int num3 = 0;
						int num4 = 0;
						int num5 = 156;
						bool flag = false;
						int num6 = 0;
						dealDataHandler(EVENT_CODE.TesterDownloadPro, "0");
						while (true)
						{
							if (!flag)
							{
								if (num2 + num5 <= buf.Length)
								{
									num3 = num5;
								}
								else
								{
									num3 = buf.Length - num2;
									flag = true;
								}
								TRULE_DOWN down = default(TRULE_DOWN);
								down.State = 1;
								down.Addr = (ushort)num2;
								down.Len = (byte)num3;
								down.CmdBuf = new byte[down.Len];
								Array.Copy(buf, down.Addr, down.CmdBuf, 0, down.Len);
								RuleDownFlag = ERuleDown.Idle;
								num4 = 0;
								RuleDown(down);
								while (RuleDownFlag == ERuleDown.Idle)
								{
									Thread.Sleep(10);
									if (++num4 <= 200)
									{
										continue;
									}
									goto IL_0184;
								}
								if (RuleDownFlag == ERuleDown.Err)
								{
									dealDataHandler(EVENT_CODE.TesterDownload, "存储异常退出，请注意！");
									break;
								}
								int num7 = (num2 + num3) * 100 / buf.Length;
								if (num7 != num6)
								{
									num6 = num7;
									dealDataHandler(EVENT_CODE.TesterDownloadPro, num7.ToString());
								}
								if (!flag)
								{
									num2 += num3;
									continue;
								}
								TRULE_DOWN down2 = new TRULE_DOWN
								{
									State = 2,
									Addr = 0,
									Len = 1,
									CmdBuf = new byte[down.Len]
								};
								RuleDown(down2);
							}
							dealDataHandler(EVENT_CODE.TesterDownloadPro, "100");
							dealDataHandler(EVENT_CODE.TesterDownload, "下载完成");
							break;
							IL_0184:
							dealDataHandler(EVENT_CODE.TesterDownload, "接收等待超时");
							break;
						}
						break;
					}
					Thread.Sleep(10);
					if (--num < 1)
					{
						dealDataHandler(EVENT_CODE.TesterDownload, "执行失败, 查询设备超时");
						break;
					}
				}
			}
			isDownloadStart = false;
		}).Start();
	}
}

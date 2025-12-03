using System;
using System.Collections.Generic;

namespace JX1000;

public class CBuf
{
	private List<byte> buf = new List<byte>();

	public void Clear()
	{
		buf.Clear();
	}

	public int GetLength()
	{
		return buf.Count;
	}

	public void Write(char val)
	{
		buf.Add(Convert.ToByte(val));
	}

	public void Write(char[] val)
	{
		foreach (char value in val)
		{
			buf.Add(Convert.ToByte(value));
		}
	}

	public void Write(byte val)
	{
		buf.Add(val);
	}

	public void Write(byte[] val)
	{
		buf.AddRange(val);
	}

	public void Write(ushort val)
	{
		buf.Add((byte)(val & 0xFF));
		buf.Add((byte)((val >> 8) & 0xFF));
	}

	public void Write(ushort[] val)
	{
		for (int i = 0; i < val.Length; i++)
		{
			buf.Add((byte)(val[i] & 0xFF));
			buf.Add((byte)((val[i] >> 8) & 0xFF));
		}
	}

	public void Write(uint val)
	{
		buf.Add((byte)(val & 0xFF));
		buf.Add((byte)((val >> 8) & 0xFF));
		buf.Add((byte)((val >> 16) & 0xFF));
		buf.Add((byte)((val >> 24) & 0xFF));
	}

	public void Write(float val)
	{
		byte[] bytes = BitConverter.GetBytes(val);
		buf.AddRange(bytes);
	}

	public byte[] ToBytes()
	{
		return buf.ToArray();
	}
}

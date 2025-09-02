using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using GPCSClientLib;
using OpenCvSharp;

namespace DataLogger
{
    /// <summary>
    /// 参数类条目
    /// </summary>
    public class ParameterEntry
    { 
        public DateTime Timestamp { get; set; }//记录时间戳
        public string SampleName { get; set; }//记录样品名称
        public double HVVoltage {  get; set; }//高压
        public int Magnification {  get; set; }//放大率
        public double WD {  get; set; }//系统读取的WD值
        public double Lens2 {  get; set; }//系统读取的lens2值
        public double Lens1 {  get; set; }//系统读取的lens1值
        public int DwellTime {  get; set; }//驻留时间，单位ns

        public double GunAlignX {  get; set; }
        public double GunAlignY {  get; set; }
        public double ApertureAlignX { get;set; }
        public double ApertureAlignY { get;set; }

        public double StigX13Lsv {  get; set; }
        public double StigX2Lsv {  get; set; }
        public double StigX4Lsv {  get; set; }

        public double StigY13Lsv { get; set; }
        public double StigY2Lsv { get; set; }
        public double StigY4Lsv { get; set; }

        public double StageX {  get; set; }
        public double StageY { get; set; }
        public double StageZ { get; set; }
        public double StageR { get; set; }

        public double DetPMT { get; set; }
    }

    /// <summary>
    /// 日志条目类，用于读取日志文件
    /// </summary>
    public class LogEntry
    {
        public DateTime Timestamp { get; set; }
        public string ParameterName { get; set; }
        public object Value { get; set; }

        public LogEntry(DateTime time, string paramName, object value)
        {
            Timestamp = time;
            ParameterName = paramName;
            Value = value;
        }
    }

    public class ParameterLog : IDisposable
    {
        private bool _isLogging = false;
        private string _logFilePath;
        private string _logFolderPath;
        private string _currentSessionId;
        private StreamWriter _logWriter;
        private bool _isDisposed;

        //线程安全队列存储日志条目
        private readonly ConcurrentQueue<LogEntry> _logQueue = new ConcurrentQueue<LogEntry>();

        //取消令牌，正确关闭后台任务
        private CancellationTokenSource _cts;

        private static readonly ParameterLog parameterLog = new ParameterLog();
        public static ParameterLog Instance {  get { return parameterLog; } }

        private ParameterLog() {
            _logFolderPath = _logFolderPath ?? Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "ParamAlignLog");

            // 确保日志文件夹存在
            if (!Directory.Exists(_logFolderPath))
            {
                Directory.CreateDirectory(_logFolderPath);
            }

            ClientLib.Instance.ParameterChangedInt += Instance_ParameterChangedInt;
            ClientLib.Instance.ParameterChangedDouble += Instance_ParameterChangedDouble;
        }

        public Task SaveImgAndStopLoggingAsync(object o)
        {
            return Task.CompletedTask;
        }

        //~ParameterLog()
        //{
        //    try
        //    {
        //        // 取消事件订阅
        //        ClientLib.Instance.ParameterChangedInt -= Instance_ParameterChangedInt;
        //        ClientLib.Instance.ParameterChangedDouble -= Instance_ParameterChangedDouble;

        //        // 关闭文件
        //        _logWriter?.Close();
        //        _logWriter?.Dispose();
        //    }
        //    catch 
        //    {

        //    }
        //}
        ~ParameterLog()
        {
            Dispose(false);
        }
        private void Instance_ParameterChangedInt(object sender, GPCSCommon.ParamChangedEventArgs e)
        {
            if(!_isLogging) return;

            switch (e.ParamName)
            {
                case "Scan.DwellLsv":
                case "SEMC.Mag":

                case "SEMC.GunAlignX":
                case "SEMC.GunAlignY":
                case "SEMC.StigX13":
                case "SEMC.StigX2":
                case "SEMC.StigX4":
                case "SEMC.StigY13":
                case "SEMC.StigY2":
                case "SEMC.StigY4":
                case "SEMC.Lens1Lsv":
                case "SEMC.Lens2Lsv":
                    EnqueueLogEntry(DateTime.Now, e.ParamName, ClientLib.Instance.GetParam(e.ParamName, -1));
                    //Log(DateTime.Now, e.ParamName, ClientLib.Instance.GetParam(e.ParamName, -1));
                    break;
                default:
                    break;
            }
        }

        private void Instance_ParameterChangedDouble(object sender, GPCSCommon.ParamChangedEventArgs e)
        {
            switch (e.ParamName)
            {
                case "SEMC.HVVoltage":
                case "SEMC.WD":
                case "SEMC.Fov":

                case "Stage.X":
                case "Stage.Y":
                case "Stage.Z":
                case "Stage.R":

                case "Det.SE2PMTVLsv":
                case "Det.InlensPMTVLsv":
                    //Log(DateTime.Now, e.ParamName, ClientLib.Instance.GetParam(e.ParamName, 0.0));
                    EnqueueLogEntry(DateTime.Now, e.ParamName, ClientLib.Instance.GetParam(e.ParamName, 0.0));
                    break;
                default:
                    break;
            }
        }

        //讲日志条目添加到队列
        private void EnqueueLogEntry(DateTime time, string paramName, object value)
        {
            _logQueue.Enqueue(new LogEntry(time, paramName, value));
        }


        public void StartLogging()
        {
            if (_isLogging) return;

            _isLogging = true;

            _currentSessionId = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            _logFilePath = Path.Combine(_logFolderPath, $"ParamLog_{_currentSessionId}.csv");

            try
            {
                // 创建或覆盖日志文件
                _logWriter = new StreamWriter(_logFilePath, false, Encoding.UTF8);

                // 写入CSV头部
                _logWriter.WriteLine("Time,ParameterName,Value");

                // 记录开始日志
                //Log(DateTime.Now, "SessionStart", "1");
                EnqueueLogEntry(DateTime.Now, "SessionStart", "1");

                // 确保写入磁盘
                _logWriter.Flush();

                //启动后台任务处理日志队列
                _cts = new CancellationTokenSource();
                Task.Run(()=> ProcessLogQueue(_cts.Token), _cts.Token);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error starting log session: {ex.Message}");
                _isLogging = false;
            }
        }

        //后台任务，处理日志队列
        private async Task ProcessLogQueue(CancellationToken token)
        {
            while(!token.IsCancellationRequested)
            {
                //处理队列中的所有条目
                int processedCount = 0;

                while(_logQueue.TryDequeue(out LogEntry entry) && !token.IsCancellationRequested)
                {
                    try
                    {
                        if(_logWriter != null)
                        {
                            //转换为CSV
                            string csvLine = $"{entry.Timestamp:yyyy-MM-dd HH:mm:ss.fff},{entry.ParameterName},{entry.Value}";
                            _logWriter.WriteLine(csvLine);

                            processedCount++;

                            //每处理一定数量的条目，刷新到磁盘
                            if (processedCount >= 10)
                            {
                                _logWriter.Flush();
                                processedCount = 0;
                            }
                        }
                    }
                    catch(Exception ex)
                    {
                        Console.WriteLine($"Error writing to log : {ex.Message}");
                    }
                }

                // 如果处理了一些条目但不足以触发刷新，则在这里刷新
                if (processedCount > 0 && _logWriter != null)
                {
                    _logWriter.Flush();
                }

                // 休眠一小段时间以避免CPU占用过高
                await Task.Delay(50, token).ConfigureAwait(false);
            }
        }


        /// <summary>
        /// 记录参数到日志文件
        /// </summary>
        private void Log(DateTime time, string paramName, object value)
        {
            if (!_isLogging || _logWriter == null)
                return;

            try
            {
                // 格式化为CSV行
                string csvLine = $"{time:yyyy-MM-dd HH:mm:ss.fff},{paramName},{value}";
                _logWriter.WriteLine(csvLine);
                _logWriter.Flush();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error writing to log: {ex.Message}");
            }
        }

        public string SaveImgAndStopLogging(byte[] image)
        {
            if (!_isLogging) return null;

            try
            {
                double HVVoltage = ClientLib.Instance.GetParam("SEMC.HVVoltage", 0.0);
                int Mag = ClientLib.Instance.GetParam("SEMC.Mag", 0);
                double WD = ClientLib.Instance.GetParam("SEMC.WD", 0.0);

                // 保存图像
                string imageFileName = $"PerfectImage_{_currentSessionId}_HV_{HVVoltage:0.0}_Mag_{Mag.ToString()}_WD_{WD:0.0}_mm.png";
                string imageFilePath = Path.Combine(_logFolderPath, imageFileName);

                SaveImage(image, imageFilePath);

                //确保队列中的日志都被处理
                EnqueueLogEntry(DateTime.Now, "PerfectImage", imageFilePath);
                EnqueueLogEntry(DateTime.Now, "SessionEnd", "0");

                //// 记录图像保存信息
                //Log(DateTime.Now, "PerfectImage", imageFilePath);

                //// 记录会话结束
                //Log(DateTime.Now, "SessionEnd", "0");

                //停止日志处理任务
                _cts.Cancel();

                //给后台处理任务一些时间来处理剩余的日志条目
                Thread.Sleep(200);

                //确保所有的日志条目都被写入
                while (_logQueue.TryDequeue(out LogEntry entry))
                {
                    if (_logWriter != null)
                    {
                        string csvLine = $"{entry.Timestamp:yyyy-MM-dd HH:mm:ss.fff},{entry.ParameterName},{entry.Value}";
                        _logWriter.WriteLine(csvLine);
                    }
                }

                // 关闭日志文件
                if (_logWriter != null)
                {
                    _logWriter.Flush();
                    _logWriter.Close();
                    _logWriter.Dispose();
                    _logWriter = null;
                }

                _isLogging = false;

                return imageFilePath;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error saving perfect image: {ex.Message}");
                return null;
            }
        }

        private void SaveImage(byte[] image, string imageFilePath)
        {
            Mat ScaledImg = ImageProcess.BufferToMat(image);

            ImageProcess.SaveImage(ScaledImg, imageFilePath);
        }

        public void Dispose()
        {
            Dispose(true);
            GC.SuppressFinalize(this);
        }

        protected virtual void Dispose(bool disposing)
        {
            if(_isDisposed) return;

            if (disposing)
            {
                // 释放托管资源
                if (_cts != null)
                {
                    _cts.Cancel();
                    _cts.Dispose();
                    _cts = null;
                }

                if (_logWriter != null)
                {
                    _logWriter.Flush();
                    _logWriter.Close();
                    _logWriter.Dispose();
                    _logWriter = null;
                }

                // 移除事件处理程序
                ClientLib.Instance.ParameterChangedInt -= Instance_ParameterChangedInt;
                ClientLib.Instance.ParameterChangedDouble -= Instance_ParameterChangedDouble;
            }

            _isDisposed = true;
        }
        


        // 还未验证
        /// <summary>
        /// 读取已记录的日志文件
        /// </summary>
        public static List<LogEntry> ReadLogFile(string filePath)
        {
            var entries = new List<LogEntry>();

            if (!File.Exists(filePath))
                return entries;

            using (var reader = new StreamReader(filePath, Encoding.UTF8))
            {
                // 跳过标题行
                reader.ReadLine();

                string line;
                while ((line = reader.ReadLine()) != null)
                {
                    string[] parts = line.Split(',');
                    if (parts.Length >= 3)
                    {
                        entries.Add(new LogEntry(DateTime.Parse(parts[0]), parts[1], parts[2]));
                        //{
                        //    Timestamp = DateTime.Parse(parts[0]),
                        //    ParameterName = parts[1],
                        //    Value = parts[2]
                        //});
                    }
                }
            }

            return entries;
        }

        /// <summary>
        /// 获取所有可用的日志会话
        /// </summary>
        public static List<string> GetAvailableSessions(string logFolderPath = null)
        {
            string folderPath = logFolderPath ?? Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "ParamLog");
            var sessions = new List<string>();

            if (!Directory.Exists(folderPath))
                return sessions;

            var logFiles = Directory.GetFiles(folderPath, "ParamLog_*.csv");

            foreach (var file in logFiles)
            {
                var fileName = Path.GetFileNameWithoutExtension(file);
                if (fileName.StartsWith("ParamLog_"))
                {
                    sessions.Add(fileName.Substring(9)); // 移除 "ParamLog_" 前缀
                }
            }

            return sessions;
        }
    }
}

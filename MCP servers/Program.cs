using devDept.Eyeshot.Entities;
using GearDesign.Infrastructure;
using GearDesign.Utility;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using System;
using System.Diagnostics;
using System.IO;
using System.Linq.Expressions;
using System.Runtime.InteropServices;
using System.Runtime.Versioning;
using System.Threading;
using System.Threading.Tasks;  // ⭐ 추가
using System.Windows.Forms;

namespace GearDesign
{
    static class Program
    {
        [DllImport("kernel32.dll")]
        static extern bool AllocConsole();

        [DllImport("kernel32.dll")]
        static extern bool AttachConsole(int dwProcessId);

        [STAThread]
        [SupportedOSPlatform("windows")]
        static void Main(string[] args)
        {
            if (args.Length > 0 && args[0] == "--ipc-mode")
            {
                if (!AttachConsole(-1))
                {
                    AllocConsole();
                }

                // ⭐ Wait() 추가하여 비동기 메서드 동기 실행
                RunIpcMode().Wait();
                return;
            }

            bool ok = Application.SetHighDpiMode(HighDpiMode.PerMonitorV2);
            Debug.WriteLine($"PMv2 set: {ok}");

            string deploymebtkey = "lgCAABrIdt9CC9sBJABVcGRhdGVhYmxlVGlsbD0yMDI1LTA5LTIwI1JldmlzaW9uPTABDXZ255CgPJB54y3bmjNy6RfmL4XoM1K6ZifuQSuNMerrdvltn+POD+k5RK8DuYQUFg3s35Xt4gOt4L9Q7QRACfaFjChWXrWPFznt9lTR8i8ZRy7XzbCagjKt+UxUAaYZAnjr3SoIdsoWC0FsxLyUzfAkjEgcMHT0PI3xn3guDB3TUczni6osV8Z7FP9KiMCu3G+csrGf9LOMO1unEBOFG+X2QwRTAhZncr7wMfFllxRCJUtXb1Z4P27NUYG6SkMb9korEs6xKVj8Pi+U1BFj31tGcEXbmP2vOOgXNVJIcnqW9B8JTYJ2D+ckGccdH6Z53q0TJtSMviPEWDlhhy/115MhPFVA0RnOJluNTy8E7HmMxVmQC8ndA7PIz8EF4y2EauM1HF/KeT6I5q2A6ldq1jFl8jVERKTGnaq/qNlWXO7WmWQ0hie8rtgQhmp+hRSLzAJodIS6jtLazML/osCBQ+DI3zSFNetK4pvea69ZXbjRYhvRi/9Bvmjbtl0+0RUpCw==";

            LightningChartLib.WinForms.Charting.LightningChart.SetDeploymentKey(deploymebtkey);

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new GearDesignForm());
        }

        // ⭐ async Task로 변경
        static async Task RunIpcMode()
        {
            try
            {
                var stdin = Console.OpenStandardInput();
                var stdout = Console.OpenStandardOutput();
                Console.SetIn(new StreamReader(stdin));
                Console.SetOut(new StreamWriter(stdout) { AutoFlush = true });

                var form = new GearDesignForm(AppDomain.CurrentDomain.BaseDirectory);
                form.Initial_Load();

                Console.Error.WriteLine("IPC 모드 시작됨");

                string line;
                while ((line = Console.ReadLine()) != null)
                {
                    try
                    {
                        var command = JObject.Parse(line);
                        // ⭐ await 추가
                        var response = await ProcessCommand(form, command);

                        Console.WriteLine(JsonConvert.SerializeObject(response));
                    }
                    catch (Exception ex)
                    {
                        var error = new { success = false, error = ex.Message, stack = ex.StackTrace };
                        Console.WriteLine(JsonConvert.SerializeObject(error));
                    }
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"IPC 오류: {ex}");
            }
        }

        // ⭐ 진행 상황 전송 헬퍼 함수 추가 - 버퍼 즉시 비우기
        static void SendProgress(string message, int? percentage = null)
        {
            try
            {
                var progress = new
                {
                    type = "progress",
                    message = message,
                    percentage = percentage,
                    timestamp = DateTime.Now.ToString("o")
                };
                Console.WriteLine(JsonConvert.SerializeObject(progress));
                Console.Out.Flush(); // ⭐ 버퍼 즉시 비우기
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"[ERROR] SendProgress 실패: {ex.Message}");
            }
        }

        // ⭐ async Task<object>로 변경
        static async Task<object> ProcessCommand(GearDesignForm form, JObject command)
        {
            string action = command["action"]?.ToString();

            try
            {
                switch (action)
                {
                    case "get_default_config":
                        var defaultConfig = form.SaveDataInput_Json(true);
                        return new
                        {
                            type = "result",  // ⭐ 타입 추가
                            success = true,
                            config = defaultConfig
                        };

                    case "load_and_validate_config":
                        var config = (JObject)command?["config"];

                        if (config == null)
                            return new { type = "result", success = false, error = "command에 불러올 데이터가 없습니다." };

                        var dataValid = form.LoadData_Validation(config);
                        if (!dataValid.IsValid)
                            return new { type = "result", success = false, error = $"데이터 검증 실패: \n\n{string.Join("\n", dataValid.Errors)}" };

                        form.LoadDataInput_Json(config);

                        return new { type = "result", success = true };

                    case "calc_geometry":
                        form.ClearMessages();
                        var geomResult = form.CalcGeometry();
                        return new
                        {
                            type = "result",
                            success = true,
                            results = geomResult
                        };

                    case "calc_loadcase":
                        var geomResults = (JObject)command?["geometry_data"];

                        if (geomResults == null)
                            return new { type = "result", success = false, error = "command에 치형데이터가 없습니다." };

                        var loadResult = form.CalcLoadCase(geomResults);
                        var message = form.GetMessages();

                        return new
                        {
                            type = "result",
                            success = true,
                            results = loadResult,
                            messages = message
                        };

                    case "calculate":
                        form.ClearMessages();
                        var geomResult2 = form.CalcGeometry();
                        var loadResult2 = form.CalcLoadCase(geomResult2);
                        var message2 = form.GetMessages();

                        return new
                        {
                            type = "result",
                            success = true,
                            results = loadResult2,
                            messages = message2
                        };

                    case "get_messages":
                        var result_message = form.GetMessages();

                        return new
                        {
                            type = "result",
                            success = true,
                            messages = result_message
                        };

                    case "save_2D_image":
                        string path = command["path"]?.ToString();

                        if (path == null)
                            return new { type = "result", success = false, error = "command에 저장할 경로가 없습니다." };

                        bool success = form.SaveGearImage(path);
                        return new
                        {
                            type = "result",
                            success = success
                        };

                    case "save_3d_modeling":
                        string path3D = command["path"]?.ToString();
                        if (path3D == null)
                            return new { type = "result", success = false, error = "command에 저장할 경로가 없습니다." };
                        bool success3D = form.Save3DGearModeling(path3D);
                        return new { type = "result", success = success3D };

                    case "save_3d_image":
                        string imgPath = command["path"]?.ToString();
                        if (imgPath == null)
                            return new { type = "result", success = false, error = "command에 저장할 경로가 없습니다." };

                        int width = command["width"]?.ToObject<int>() ?? 800;
                        int height = command["height"]?.ToObject<int>() ?? 600;
                        bool imgSuccess = form.Save3DGearImage(imgPath, width, height);
                        return new { type = "result", success = imgSuccess };

                    case "save_report":
                        string reportPath = command["path"]?.ToString();
                        if (reportPath == null)
                            return new { type = "result", success = false, error = "command에 저장할 경로가 없습니다." };

                        var reportConfig = (JObject)command["config"];
                        bool reportSuccess = form.SaveGearReport(reportPath, reportConfig);
                        return new { type = "result", success = reportSuccess };

                    case "get_all_results_summary":
                        var resultsObj = (JObject)command?["results"];
                        if (resultsObj == null)
                            return new { type = "result", success = false, error = "results 데이터가 필요합니다" };

                        var allsummary = form.GetAllResultSummary(resultsObj);
                        return new
                        {
                            type = "result",
                            success = true,
                            summary = allsummary
                        };

                    // ⭐⭐⭐ simple_sizing_gearpair - 진행 상황 전송 추가 ⭐⭐⭐
                    case "simple_sizing_gearpair":
                        var modifydata = (JObject)command?["modify_data"];
                        SimpleSizingInput _input = form.SetDefaultValue_SimpleSizing_Pair();

                        if (modifydata != null)
                            _input.SetFromJObject(modifydata);

                        SendProgress("사이징 계산 초기화 중...", 0);

                        using (var cts = new CancellationTokenSource(TimeSpan.FromMinutes(5)))
                        {
                            try
                            {
                                SendProgress("파라미터 검증 중...", 10);

                                // ⭐ 진행률 콜백 액션 생성 - stdout 버퍼 블로킹 방지
                                Action<int, int> progressAction = (current, total) =>
                                {
                                    try
                                    {
                                        int percentage = (int)((double)current / total * 80) + 10; // 10%~90% 범위
                                        SendProgress($"계산 중... ({current}/{total})", percentage);
                                        Console.Out.Flush(); // ⭐⭐⭐ 버퍼 즉시 비우기 (데드락 방지)
                                    }
                                    catch (Exception ex)
                                    {
                                        Console.Error.WriteLine($"[ERROR] Progress callback 실패: {ex.Message}");
                                    }
                                };

                                Console.Error.WriteLine("[DEBUG] Calculate 호출 전");
                                Console.Error.Flush();

                                // ⭐ Task.Run으로 감싸서 SynchronizationContext 제거 (데드락 방지)
                                var results = await Task.Run(async () =>
                                {
                                    return await SimpleSizing.Calculate(
                                        _input,
                                        true,              // withRating
                                        true,              // useParallel = true
                                        progressAction,    // progress callback
                                        cts.Token          // cancellation token
                                    );
                                }, cts.Token);

                                Console.Error.WriteLine("[DEBUG] Calculate 완료! 반환값 확인 시작");
                                Console.Error.WriteLine($"[DEBUG] results != null: {results != null}");
                                Console.Error.WriteLine($"[DEBUG] totalcases: {results?.totalcases}");
                                Console.Error.Flush();

                                SendProgress("계산 완료, 결과 정리 중...", 90);

                                return new
                                {
                                    type = "result",
                                    success = true,
                                    inputs = _input.GetJson(),
                                    total_cases = results.totalcases,
                                    filtered_cases = results.Filteredcases,
                                    filtered_results = results.FilteredResults
                                };
                            }
                            catch (OperationCanceledException)
                            {
                                return new { type = "result", success = false, error = "Operation cancelled" };
                            }
                            catch (Exception ex)
                            {
                                return new { type = "result", success = false, error = ex.Message };
                            }
                        }

                    case "simple_sizing_gearpair_get_input":
                        _input = new SimpleSizingInput();
                        try
                        {
                            _input = form.SetDefaultValue_SimpleSizing_Pair();
                            var getinput = _input.GetJson();

                            return new
                            {
                                type = "result",
                                success = true,
                                inputs = _input.GetJson()
                            };
                        }
                        catch (Exception ex)
                        {
                            return new
                            {
                                type = "result",
                                success = false,
                                error = ex.ToString()
                            };
                        }

                    default:
                        return new { type = "result", success = false, error = $"Unknown action: {action}" };
                }
            }
            catch (Exception ex)
            {
                return new { type = "result", success = false, error = ex.Message, details = ex.ToString() };
            }
        }
    }
}
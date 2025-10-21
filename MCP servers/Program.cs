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
                // ⭐ UTF-8 인코딩 설정 (BOM 없이, 한글 깨짐 방지)
                var utf8WithoutBom = new System.Text.UTF8Encoding(false);  // BOM 제거
                Console.OutputEncoding = utf8WithoutBom;
                Console.InputEncoding = utf8WithoutBom;

                var stdin = Console.OpenStandardInput();
                var stdout = Console.OpenStandardOutput();
                var stderr = Console.OpenStandardError();

                Console.SetIn(new StreamReader(stdin, utf8WithoutBom));
                Console.SetOut(new StreamWriter(stdout, utf8WithoutBom) { AutoFlush = true });
                Console.SetError(new StreamWriter(stderr, utf8WithoutBom) { AutoFlush = true });

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

        // ⭐ 진행 상황 전송 헬퍼 함수 추가
        static void SendProgress(string message, int? percentage = null)
        {
            var progress = new
            {
                type = "progress",
                message = message,
                percentage = percentage,
                timestamp = DateTime.Now.ToString("o")
            };
            Console.WriteLine(JsonConvert.SerializeObject(progress));
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
                        Console.Error.WriteLine("Default 설정 로드 시작");
                        var defaultConfig = form.SaveDataInput_Json(true);

                        return new
                        {
                            type = "result",  // ⭐ 타입 추가
                            success = true,
                            config = defaultConfig
                        };

                    case "load_and_validate_config":
                        Console.Error.WriteLine("데이터 검증 및 로드 시작");
                        var config = (JObject)command?["config"];

                        if (config == null)
                            return new { type = "result", success = false, error = "command에 불러올 데이터가 없습니다." };

                        var dataValid = form.LoadData_Validation(config);
                        if (!dataValid.IsValid)
                            return new { type = "result", success = false, error = $"데이터 검증 실패: \n\n{string.Join("\n", dataValid.Errors)}" };

                        form.LoadDataInput_Json(config);

                        return new { type = "result", success = true };

                    case "calc_geometry":
                        Console.Error.WriteLine("Geometry 계산 시작");
                        form.ClearMessages();
                        var geomResult = form.CalcGeometry();
                        return new
                        {
                            type = "result",
                            success = true,
                            results = geomResult
                        };

                    case "calc_loadcase":
                        Console.Error.WriteLine("Load case 계산 시작");
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
                        Console.Error.WriteLine("Geometry 및 Load case 계산 시작");
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
                        Console.Error.WriteLine("Get messages");
                        var result_message = form.GetMessages();

                        return new
                        {
                            type = "result",
                            success = true,
                            messages = result_message
                        };

                    case "save_2D_image":
                        Console.Error.WriteLine("2D image 저장 시작");
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
                        Console.Error.WriteLine("3D 모델링 저장 시작");
                        string path3D = command["path"]?.ToString();
                        if (path3D == null)
                            return new { type = "result", success = false, error = "command에 저장할 경로가 없습니다." };
                        bool success3D = form.Save3DGearModeling(path3D);
                        return new { type = "result", success = success3D };

                    case "save_3d_image":
                        Console.Error.WriteLine("3D image 저장 시작");
                        string imgPath = command["path"]?.ToString();
                        if (imgPath == null)
                            return new { type = "result", success = false, error = "command에 저장할 경로가 없습니다." };

                        int width = command["width"]?.ToObject<int>() ?? 800;
                        int height = command["height"]?.ToObject<int>() ?? 600;
                        bool imgSuccess = form.Save3DGearImage(imgPath, width, height);
                        return new { type = "result", success = imgSuccess };

                    case "save_report":
                        Console.Error.WriteLine("Report 저장 시작");
                        string reportPath = command["path"]?.ToString();
                        if (reportPath == null)
                            return new { type = "result", success = false, error = "command에 저장할 경로가 없습니다." };

                        var reportConfig = (JObject)command["config"];
                        bool reportSuccess = form.SaveGearReport(reportPath, reportConfig);
                        return new { type = "result", success = reportSuccess };

                    case "get_all_results_summary":
                        Console.Error.WriteLine("모든 결과 요약 정보 가져오기");
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
                        Console.Error.WriteLine("Simple Sizing (Gear Pair) 계산 시작");
                        SendProgress("Verifying parameters...", 0);

                        var modifydata = (JObject)command?["modify_data"];
                        SimpleSizingInput _input = form.SetDefaultValue_SimpleSizing_Pair();

                        if (modifydata != null)
                            _input.SetFromJObject(modifydata);

                        using (var cts = new CancellationTokenSource(TimeSpan.FromMinutes(3)))
                        {
                            try
                            {

                                // ⭐ 진행률 콜백 액션 생성
                                Action<int, int> progressAction = (current, total) =>
                                {
                                    int percentage = (int)((double)current / total * 100); // 0%~100% 범위
                                    SendProgress($"Calculating... ({current}/{total})", percentage);
                                };

                                // ⭐ 5개 파라미터 버전 사용
                                var results = await SimpleSizing.Calculate(
                                    _input,
                                    true,              // withRating
                                    false,             // useParallel (병렬 처리 여부)
                                    progressAction,    // progress callback
                                    cts.Token          // cancellation token
                                );

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
                        Console.Error.WriteLine("Simple Sizing (Gear Pair) 기본 입력값 가져오기");
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
using GearCalculation;
using GearDesign.Efficiency;
using Newtonsoft.Json.Linq;
using System;
using System.Collections.Generic;
using System.Data;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using static System.Windows.Forms.VisualStyles.VisualStyleElement;

namespace GearDesign.Utility
{
    public class SimpleSizingInput
    {
        public double target_GR { get; set; }       // 목표 기어비, z2 / z1
        public double target_GR_dev { get; set; }   // 목표 기어비 편차, %
        public int z_pinion_min { get; set; }       // Case study를 수행할 피니언 최소 잇수
        public int z_pinion_max { get; set; }       // Case study를 수행할 피니언 최대 잇수
        public int z_pinion_step { get; set; }      // Case study를 수행할 피니언 최소/최대 사이 Step 잇수
        public int hunting { get; set; }         // 잇수비 최소공배수 허용 정의, (0 = allow hunting, 1 = allow partial hunting, 2 = allow no hunting)
        public double m_n_min { get; set; }       // Case study를 수행할 minimum normal module, mm
        public double m_n_max { get; set; }       // Case study를 수행할 maximum normal module, mm
        public double m_n_step { get; set; }        // Case study를 수행할 normal module step, mm

        public double a_max { get; set; }       // allowable maximum center distance, mm
        public double a_min { get; set; }       // allowable minimum center distance, mm
        public double d_max { get; set; }       // allowable maximum outer diameter, mm
        public double d_min { get; set; }       // allowable minimum outer diameter, mm
        public int maxcases { get; set; }       // maximum number of cases to return

        public double helix_angle { get; set; }  // Helix angle, deg (참고값)
        public double face_width { get; set; }   // Face width, mm (참고값)

        public double pressure_angle { get; set; } // Pressure angle, deg (참고값)
        public double min_contact_safety_factor { get; set; } // Minimum contact safety factor (S_H)
        public double min_bending_safety_factor { get; set; } // Minimum bending safety factor (S_F)
        public GearDesignForm mainForm { get; set; } // Reference to the main form for additional parameters

        /// <summary>
        /// JSON 문자열로부터 SimpleSizingInput 값을 설정합니다.
        /// </summary>
        /// <param name="jsonString">JSON 형식의 입력 데이터</param>
        public void SetFromJsonString(string jsonString)
        {
            JObject json = JObject.Parse(jsonString);
            SetFromJObject(json);
        }

        /// <summary>
        /// JObject로부터 SimpleSizingInput 값을 설정합니다.
        /// </summary>
        /// <param name="json">JObject 형식의 입력 데이터</param>
        public void SetFromJObject(JObject json)
        {
            if (json["target_GR"] != null) target_GR = json["target_GR"].Value<double>();
            if (json["target_GR_dev"] != null) target_GR_dev = json["target_GR_dev"].Value<double>();
            if (json["z_pinion_min"] != null) z_pinion_min = json["z_pinion_min"].Value<int>();
            if (json["z_pinion_max"] != null) z_pinion_max = json["z_pinion_max"].Value<int>();
            if (json["z_pinion_step"] != null) z_pinion_step = json["z_pinion_step"].Value<int>();
            if (json["hunting"] != null) hunting = json["hunting"].Value<int>();
            if (json["m_n_min"] != null) m_n_min = json["m_n_min"].Value<double>();
            if (json["m_n_max"] != null) m_n_max = json["m_n_max"].Value<double>();
            if (json["m_n_step"] != null) m_n_step = json["m_n_step"].Value<double>();
            if (json["a_max"] != null) a_max = json["a_max"].Value<double>();
            if (json["a_min"] != null) a_min = json["a_min"].Value<double>();
            if (json["d_max"] != null) d_max = json["d_max"].Value<double>();
            if (json["d_min"] != null) d_min = json["d_min"].Value<double>();
            if (json["maxcases"] != null) maxcases = json["maxcases"].Value<int>();
            if (json["helix_angle"] != null) helix_angle = json["helix_angle"].Value<double>();
            if (json["face_width"] != null) face_width = json["face_width"].Value<double>();
            if (json["pressure_angle"] != null) pressure_angle = json["pressure_angle"].Value<double>();
            if (json["min_contact_safety_factor"] != null) min_contact_safety_factor = json["min_contact_safety_factor"].Value<double>();
            if (json["min_bending_safety_factor"] != null) min_bending_safety_factor = json["min_bending_safety_factor"].Value<double>();
        }

        /// <summary>
        /// LLM이 인식할 수 있도록 현재 입력값과 메타데이터가 포함된 JSON을 반환합니다.
        /// </summary>
        /// <returns>메타데이터가 포함된 JObject</returns>
        public JObject GetJson()
        {
            JObject json = new JObject();

            json["target_GR"] = target_GR;
            json["$target_GR"] = "목표 기어비 (z2 / z1), type: double";

            json["target_GR_dev"] = target_GR_dev;
            json["$target_GR_dev"] = "목표 기어비 편차 (%), type: double";

            json["z_pinion_min"] = z_pinion_min;
            json["$z_pinion_min"] = "Case study를 수행할 피니언 최소 잇수, type: int";

            json["z_pinion_max"] = z_pinion_max;
            json["$z_pinion_max"] = "Case study를 수행할 피니언 최대 잇수, type: int";

            json["z_pinion_step"] = z_pinion_step;
            json["$z_pinion_step"] = "Case study를 수행할 피니언 최소/최대 사이 Step 잇수, type: int";

            json["hunting"] = hunting;
            json["$hunting"] = "잇수비 최소공배수 허용 정의 (0 = allow hunting, 1 = allow partial hunting, 2 = allow no hunting), type: int";

            json["m_n_min"] = m_n_min;
            json["$m_n_min"] = "Case study를 수행할 minimum normal module (mm), type: double";

            json["m_n_max"] = m_n_max;
            json["$m_n_max"] = "Case study를 수행할 maximum normal module (mm), type: double";

            json["m_n_step"] = m_n_step;
            json["$m_n_step"] = "Case study를 수행할 normal module step (mm), type: double";

            json["a_max"] = a_max;
            json["$a_max"] = "allowable maximum center distance (mm), type: double";

            json["a_min"] = a_min;
            json["$a_min"] = "allowable minimum center distance (mm), type: double";

            json["d_max"] = d_max;
            json["$d_max"] = "allowable maximum outer diameter (mm), type: double";

            json["d_min"] = d_min;
            json["$d_min"] = "allowable minimum outer diameter (mm), type: double";

            json["maxcases"] = maxcases;
            json["$maxcases"] = "maximum number of cases to return, type: int";

            json["helix_angle"] = helix_angle;
            json["$helix_angle"] = "Helix angle (deg) - 참고값, type: double";

            json["face_width"] = face_width;
            json["$face_width"] = "Face width (mm) - 참고값, type: double";

            json["pressure_angle"] = pressure_angle;
            json["$pressure_angle"] = "Pressure angle (deg) - 참고값, type: double";

            json["min_contact_safety_factor"] = min_contact_safety_factor;
            json["$min_contact_safety_factor"] = "Minimum contact safety factor (S_H), type: double";

            json["min_bending_safety_factor"] = min_bending_safety_factor;
            json["$min_bending_safety_factor"] = "Minimum bending safety factor (S_F), type: double";

            return json;
        }

        /// <summary>
        /// 기본값과 메타데이터가 포함된 JSON 스키마를 반환합니다 (static 버전).
        /// </summary>
        /// <returns>메타데이터가 포함된 JObject</returns>
        public static JObject GetJsonSchema()
        {
            JObject schema = new JObject();

            schema["target_GR"] = 2.0;
            schema["$target_GR"] = "목표 기어비 (z2 / z1), type: double, default: 2.0";

            schema["target_GR_dev"] = 0.05;
            schema["$target_GR_dev"] = "목표 기어비 편차 (%), type: double, default: 0.05";

            schema["z_pinion_min"] = 17;
            schema["$z_pinion_min"] = "Case study를 수행할 피니언 최소 잇수, type: int, default: 17";

            schema["z_pinion_max"] = 30;
            schema["$z_pinion_max"] = "Case study를 수행할 피니언 최대 잇수, type: int, default: 30";

            schema["z_pinion_step"] = 1;
            schema["$z_pinion_step"] = "Case study를 수행할 피니언 최소/최대 사이 Step 잇수, type: int, default: 1";

            schema["hunting"] = 0;
            schema["$hunting"] = "잇수비 최소공배수 허용 정의 (0 = allow hunting, 1 = allow partial hunting, 2 = allow no hunting), type: int, default: 0";

            schema["m_n_min"] = 1.0;
            schema["$m_n_min"] = "Case study를 수행할 minimum normal module (mm), type: double, default: 1.0";

            schema["m_n_max"] = 4.0;
            schema["$m_n_max"] = "Case study를 수행할 maximum normal module (mm), type: double, default: 4.0";

            schema["m_n_step"] = 0.25;
            schema["$m_n_step"] = "Case study를 수행할 normal module step (mm), type: double, default: 0.25";

            schema["a_max"] = double.PositiveInfinity;
            schema["$a_max"] = "allowable maximum center distance (mm), type: double, default: PositiveInfinity";

            schema["a_min"] = 0.0;
            schema["$a_min"] = "allowable minimum center distance (mm), type: double, default: 0.0";

            schema["d_max"] = double.PositiveInfinity;
            schema["$d_max"] = "allowable maximum outer diameter (mm), type: double, default: PositiveInfinity";

            schema["d_min"] = 0.0;
            schema["$d_min"] = "allowable minimum outer diameter (mm), type: double, default: 0.0";

            schema["maxcases"] = 5000;
            schema["$maxcases"] = "maximum number of cases to return, type: int, default: 5000";

            schema["helix_angle"] = 0.0;
            schema["$helix_angle"] = "Helix angle (deg) - 참고값, type: double, default: 0.0";

            schema["face_width"] = 10.0;
            schema["$face_width"] = "Face width (mm) - 참고값, type: double, default: 10.0";

            schema["pressure_angle"] = 20.0;
            schema["$pressure_angle"] = "Pressure angle (deg) - 참고값, type: double, default: 20.0";

            schema["min_contact_safety_factor"] = 1.2;
            schema["$min_contact_safety_factor"] = "Minimum contact safety factor (S_H), type: double, default: 1.2";

            schema["min_bending_safety_factor"] = 1.6;
            schema["$min_bending_safety_factor"] = "Minimum bending safety factor (S_F), type: double, default: 1.6";

            return schema;
        }
    }

    public class SimpleSizingOutput
    {
        public int totalcases { get; set; }
        public int calculationcases { get; set; } // Total number of cases calculated
        public int Filteredcases { get; set; }
        public DataTable GearList { get; set; }  // List of gears
        public DataTable FilteredResults { get; set; } // Sorted results based on criteria

        public double CalcTime { get; set; } // Calculation time in seconds

        /// <summary>
        /// SimpleSizingOutput을 JSON 문자열로 변환합니다.
        /// </summary>
        /// <param name="includeGearList">GearList를 포함할지 여부 (기본값: false)</param>
        /// <returns>JSON 형식의 문자열</returns>
        public string ToJsonString(bool includeGearList = false)
        {
            JObject json = ToJObject(includeGearList);
            return json.ToString();
        }

        /// <summary>
        /// SimpleSizingOutput을 JObject로 변환합니다.
        /// </summary>
        /// <param name="includeGearList">GearList를 포함할지 여부 (기본값: false)</param>
        /// <returns>JObject 형식의 데이터</returns>
        public JObject ToJObject(bool includeGearList = false)
        {
            JObject json = new JObject();

            json["totalcases"] = totalcases;
            json["calculationcases"] = calculationcases;
            json["Filteredcases"] = Filteredcases;
            json["CalcTime"] = CalcTime;

            // FilteredResults를 JArray로 변환
            if (FilteredResults != null)
            {
                JArray filteredArray = new JArray();
                foreach (DataRow row in FilteredResults.Rows)
                {
                    JObject rowObj = new JObject();
                    foreach (DataColumn col in FilteredResults.Columns)
                    {
                        rowObj[col.ColumnName] = JToken.FromObject(row[col]);
                    }
                    filteredArray.Add(rowObj);
                }
                json["FilteredResults"] = filteredArray;
            }

            // GearList는 선택적으로 포함 (데이터가 클 수 있음)
            if (includeGearList && GearList != null)
            {
                JArray gearArray = new JArray();
                foreach (DataRow row in GearList.Rows)
                {
                    JObject rowObj = new JObject();
                    foreach (DataColumn col in GearList.Columns)
                    {
                        rowObj[col.ColumnName] = JToken.FromObject(row[col]);
                    }
                    gearArray.Add(rowObj);
                }
                json["GearList"] = gearArray;
            }

            return json;
        }
    }

    public class SimpleSizing
    {
        public static async Task<SimpleSizingOutput> Calculate(SimpleSizingInput input, bool withRating, CancellationToken cancellationToken)
        {
            return await Calculate(input, withRating, false, null, cancellationToken);
        }

        public static async Task<SimpleSizingOutput> Calculate(SimpleSizingInput input, bool withRating, bool useParallel, Action<int, int> progressCallback, CancellationToken isCancelledCallback)
        {
            // 계산 시작 시간 기록
            DateTime startTime = DateTime.Now;

            // 1. 잇수 조합 계산
            DataTable gearCombinations = ExtensionMethods.CalcToothCombination_Pair(
                input.z_pinion_min, input.z_pinion_max, input.z_pinion_step, input.target_GR, input.target_GR_dev, input.hunting);

            // 2. Normal module 조합 계산
            DataTable moduleCombinations = VariableCasesCalculator.CalcNumofCases(
                input.m_n_min, input.m_n_max, input.m_n_step, "m_n [mm]");

            // 3. 전체 조합 계산
            DataTable[] allcomb = new DataTable[] { gearCombinations, moduleCombinations };
            DataTable allCombinations = VariableCasesCalculator.CalcMultiVariableCases(
                input.maxcases, allcomb);

            // 4. 기타 결과 추가
            // Gear Ratio 컬럼을 첫 번째 열에 추가
            allCombinations.Columns.Add("GearRatio", typeof(double));
            allCombinations.Columns["GearRatio"].SetOrdinal(0);

            // 각 행에 대해 Gear Ratio 계산 (z2/z1)
            foreach (DataRow row in allCombinations.Rows)
            {
                double z1 = Convert.ToDouble(row["z1"]);
                double z2 = Convert.ToDouble(row["z2"]);
                row["GearRatio"] = Math.Round(z2 / z1, 6);
            }

            // Center Distance 계산 (a = (z1 + z2) * m_n / 2)
            allCombinations.Columns.Add("a [mm]", typeof(double));
            allCombinations.Columns["a [mm]"].SetOrdinal(1);

            // 기타 정보 열 추가
            allCombinations.Columns.Add("d_a1 [mm]", typeof(double));
            allCombinations.Columns.Add("d_a2 [mm]", typeof(double));
            allCombinations.Columns.Add("α_n [deg]", typeof(double));
            allCombinations.Columns.Add("β [deg]", typeof(double));
            allCombinations.Columns.Add("Facewidth [mm]", typeof(double));

            if (withRating)
            {
                allCombinations.Columns.Add("min. S_H", typeof(string));
                allCombinations.Columns.Add("min. S_F", typeof(string));
            }

            // 5. 계산 수행 - Rating 포함 여부에 따라 순차/병렬 계산 선택
            if (withRating && useParallel)
            {
                await ProcessRowsParallel(allCombinations, input, withRating, progressCallback, isCancelledCallback);
            }
            else
            {
                await ProcessRowsSequential(allCombinations, input, withRating, progressCallback, isCancelledCallback).ConfigureAwait(false);
            }
            if (isCancelledCallback.IsCancellationRequested)
            {
                return null; // 취소 요청 시 null 반환
            }
            
            // 계산 종료 시간
            DateTime endTime = DateTime.Now;
            // 총 계산 시간
            TimeSpan calcTime = endTime - startTime;
            // 결과에 계산 시간 추가

            return CreateOutput(allCombinations, gearCombinations, moduleCombinations, calcTime, input, withRating);
        }

        private static async Task ProcessRowsSequential(DataTable allCombinations, SimpleSizingInput input, bool withRating, Action<int, int> progressCallback, CancellationToken cancellationToken)
        {
            int totalRows = allCombinations.Rows.Count;
            int processedRows = 0;

            // 병렬 처리를 위해 각 스레드마다 독립적인 객체 생성
            GearGeometryandRating G = new GearGeometryandRating();
            input.mainForm.GeometryInput(G);

            await Task.Run(() =>
            {
                foreach (DataRow row in allCombinations.Rows)
                {
                    if (cancellationToken.IsCancellationRequested)
                        break;

                    ProcessSingleRow(G, row, input, withRating);
                    processedRows++;

                    if (processedRows % Math.Max(1, totalRows / 20) == 0 || processedRows == totalRows)
                    {
                        progressCallback?.Invoke(processedRows, totalRows);
                    }
                }
            });
        }

        private static async Task ProcessRowsParallel(DataTable allCombinations, SimpleSizingInput input, bool withRating, Action<int, int> progressCallback, CancellationToken cancellationToken)
        {
            int totalRows = allCombinations.Rows.Count;
            int processedRows = 0;
            object lockObject = new object();

            // 처리된 행들을 저장할 컬렉션 (인덱스 순서 보장)
            var processedDataRows = new DataRow[totalRows];

            // 로컬 비동기 함수로 각 행 처리
            async Task ProcessRowAsync(int rowIndex)
            {
                // 취소 체크
                if (cancellationToken.IsCancellationRequested)
                    return;

                var originalRow = allCombinations.Rows[rowIndex];

                // DataRow 깊은 복사
                var copiedRow = DeepCopyDataRow(originalRow, allCombinations);

                // 비동기 작업으로 행 처리
                var processedRow = await Task.Run(() => ProcessSingleRow(copiedRow, input, withRating));

                // 처리된 행을 배열에 저장 (인덱스 순서 유지)
                processedDataRows[rowIndex] = processedRow;

                lock (lockObject)
                {
                    processedRows++;
                    // Progress 업데이트 (5% 단위로 업데이트하여 UI 부담 감소)
                    if (processedRows % Math.Max(1, totalRows / 20) == 0 || processedRows == totalRows)
                    {
                        progressCallback?.Invoke(processedRows, totalRows);
                    }
                }
            }

            // 모든 행에 대해 비동기 작업 생성
            var tasks = new List<Task>();

            for (int i = 0; i < totalRows; i++)
            {
                tasks.Add(ProcessRowAsync(i));
            }

            // 모든 작업이 완료될 때까지 대기
            await Task.WhenAll(tasks);

            // 취소되지 않았다면 원본 테이블의 데이터를 처리된 데이터로 대체
            if (!cancellationToken.IsCancellationRequested)
            {
                // 기존 행들 모두 제거
                allCombinations.Rows.Clear();

                // 처리된 행들을 순서대로 추가
                foreach (var processedRow in processedDataRows)
                {
                    if (processedRow != null) // null 체크 (취소된 작업이 있을 수 있음)
                    {
                        allCombinations.Rows.Add(processedRow.ItemArray);
                    }
                }
            }
        }

        // DataRow 깊은 복사를 위한 헬퍼 메서드
        private static DataRow DeepCopyDataRow(DataRow originalRow, DataTable targetTable)
        {
            var newRow = targetTable.NewRow();

            // 모든 컬럼 값 복사
            for (int i = 0; i < originalRow.ItemArray.Length; i++)
            {
                // 값 타입이나 string은 자동으로 복사되고,
                // 참조 타입의 경우 필요에 따라 추가적인 깊은 복사 로직이 필요할 수 있음
                newRow[i] = originalRow[i];
            }

            return newRow;
        }
        private static DataRow ProcessSingleRow(DataRow row, SimpleSizingInput input, bool withRating)
        {
            // 각 행의 데이터를 안전하게 읽기
            int z1 = Convert.ToInt16(row["z1"]);
            int z2 = Convert.ToInt16(row["z2"]);
            double m_n = Convert.ToDouble(row["m_n [mm]"]);

            var gearParams = new InvoluteHelicalGearCenterDistance.HelicalGearParameters
            {
                NormalModule = m_n,          // 법선 모듈 2mm
                Teeth1 = z1,                 // 피니언 잇수
                Teeth2 = z2,                 // 기어 잇수
                ProfileShift1 = 0,         // 피니언 전위계수
                ProfileShift2 = 0,         // 기어 전위계수
                NormalBacklash = 0,       // 법선 백래시 0.15mm
                NormalPressureAngle = input.pressure_angle,  // 법선 압력각 20도
                HelixAngle = input.helix_angle,              // 헬릭스 각 15도
                GearType1 = 1,               // 외부 기어
                GearType2 = 1                // 외부 기어
            };

            var result = InvoluteHelicalGearCenterDistance.CalculateCenterDistance(gearParams);

            row["a [mm]"] = Math.Round(result.CenterDistance, 6);

            var info = InvoluteHelicalGearCenterDistance.CalculateDetailInfo(gearParams, result);
            row["d_a1 [mm]"] = Math.Round(info.AddendumDiameter1, 6); // 피니언 외경
            row["d_a2 [mm]"] = Math.Round(info.AddendumDiameter2, 6); // 휠 외경
            row["α_n [deg]"] = input.pressure_angle;
            row["β [deg]"] = input.helix_angle;
            row["Facewidth [mm]"] = input.face_width;

            if (withRating)
            {
                try
                {
                    // 병렬 처리를 위해 각 스레드마다 독립적인 객체 생성
                    GearGeometryandRating G = new GearGeometryandRating();
                    input.mainForm.GeometryInput(G);

                    // 입력 설정 
                    G.m_n = m_n;
                    G.z[1] = z1;
                    G.z[2] = z2;
                    G.x[1] = 0;
                    G.x[2] = 0;
                    G.j_bn[1] = 0;
                    G.alpha_n = input.pressure_angle;
                    G.beta = input.helix_angle;
                    G.b[1] = input.face_width;
                    G.b[2] = input.face_width;

                    G.CDMethods = "Center distance";
                    G.CalcGeometry();

                    // mainForm 접근을 동기화
                    JObject jGear;
                    JArray jLC;
                    JArray jLC_result;
                    bool calcKV;

                    jGear = input.mainForm.SetjGear();

                    int numP = 1;
                    JArray jGeo = new JArray();
                    for (int i = 0; i < numP; i++)
                    {
                        JObject jGeoi = G.GetGeometryData(i + 1);
                        jGeo.Add(jGeoi);
                    }
                    jGear["Geometry"] = jGeo;

                    // 항상 Geometry 계산 후 사용 필요
                    double[] z = new double[4];
                    z[0] = Math.Abs(G.z[1]);
                    z[1] = Math.Abs(G.z[2]);
                    z[2] = Math.Abs(G.z[3]);
                    z[3] = Math.Abs(G.z[4]);

                    jLC = input.mainForm.GetLoadSpectrum_Duty(input.mainForm.DGV_Dutycycle, input.mainForm.DGV_Factors);
                    jLC_result = input.mainForm.CalcPowerFlow(jLC, input.mainForm.Drop_SelectGearType.SelectedIndex, z);
                    calcKV = input.mainForm.CB_CalcKV.Checked;

                    JObject jLC_total = new JObject();
                    jLC_total.Add("Gear", null);
                    jLC_total.Add("Pair", null);
                    jLC_total.Add("Efficiency", null);
                    jLC_total.Add("TotalHr", null);

                    JObject LC = new JObject();
                    LC.Add("Input", jLC);
                    LC.Add("Output", jLC_result);
                    LC.Add("Total", jLC_total);
                    jGear["LC"] = LC;

                    // 4. Geometry 및 Rating (이 부분은 병렬 처리 가능)
                    LoadSpectrum LS = new LoadSpectrum();
                    LS.LoadSpectrum_OnlyRating(jGear, G, calcKV);

                    double SHmin = ExtensionMethods.JTokentoDouble(jGear["LC"]["Total"]["S_Hmin"]);
                    double SFmin = ExtensionMethods.JTokentoDouble(jGear["LC"]["Total"]["S_Fmin"]);

                    double calcSHmin = ExtensionMethods.JTokentoDouble(jGear["LC"]["Total"]["Calculated S_Hmin"]);
                    double calcSFmin = ExtensionMethods.JTokentoDouble(jGear["LC"]["Total"]["Calculated S_Fmin"]);

                    // DataRow 접근도 동기화 (row는 lock으로 이미 보호됨)
                    row["min. S_H"] = Math.Round(calcSHmin, 6);
                    row["min. S_F"] = Math.Round(calcSFmin, 6);
                }
                catch (Exception ex)
                {
                    // Rating 계산 중 오류 발생 시 기본값 설정
                    System.Diagnostics.Debug.WriteLine($"Rating calculation error for z1={z1}, z2={z2}, m_n={m_n}: {ex.Message}");
                    row["min. S_H"] = "Error";
                    row["min. S_F"] = "Error";
                    
                    // 에러 발생 시 계속 진행
                }
            }
            return row; // 처리된 행 반환
        }

        private static DataRow ProcessSingleRow(GearGeometryandRating G, DataRow row, SimpleSizingInput input, bool withRating)
        {
            // 각 행의 데이터를 안전하게 읽기
            int z1 = Convert.ToInt16(row["z1"]);
            int z2 = Convert.ToInt16(row["z2"]);
            double m_n = Convert.ToDouble(row["m_n [mm]"]);

            var gearParams = new InvoluteHelicalGearCenterDistance.HelicalGearParameters
            {
                NormalModule = m_n,          // 법선 모듈 2mm
                Teeth1 = z1,                 // 피니언 잇수
                Teeth2 = z2,                 // 기어 잇수
                ProfileShift1 = 0,         // 피니언 전위계수
                ProfileShift2 = 0,         // 기어 전위계수
                NormalBacklash = 0,       // 법선 백래시 0.15mm
                NormalPressureAngle = input.pressure_angle,  // 법선 압력각 20도
                HelixAngle = input.helix_angle,              // 헬릭스 각 15도
                GearType1 = 1,               // 외부 기어
                GearType2 = 1                // 외부 기어
            };

            var result = InvoluteHelicalGearCenterDistance.CalculateCenterDistance(gearParams);

            row["a [mm]"] = Math.Round(result.CenterDistance, 6);

            var info = InvoluteHelicalGearCenterDistance.CalculateDetailInfo(gearParams, result);
            row["d_a1 [mm]"] = Math.Round(info.AddendumDiameter1, 6); // 피니언 외경
            row["d_a2 [mm]"] = Math.Round(info.AddendumDiameter2, 6); // 휠 외경
            row["α_n [deg]"] = input.pressure_angle;
            row["β [deg]"] = input.helix_angle;
            row["Facewidth [mm]"] = input.face_width;

            if (withRating)
            {
                try
                {                   

                    // 입력 설정 
                    G.m_n = m_n;
                    G.z[1] = z1;
                    G.z[2] = z2;
                    G.x[1] = 0;
                    G.x[2] = 0;
                    G.j_bn[1] = 0;
                    G.alpha_n = input.pressure_angle;
                    G.beta = input.helix_angle;
                    G.b[1] = input.face_width;
                    G.b[2] = input.face_width;

                    G.CDMethods = "Center distance";
                    G.CalcGeometry();

                    // mainForm 접근을 동기화
                    JObject jGear;
                    JArray jLC;
                    JArray jLC_result;
                    bool calcKV;

                    jGear = input.mainForm.SetjGear();

                    int numP = 1;
                    JArray jGeo = new JArray();
                    for (int i = 0; i < numP; i++)
                    {
                        JObject jGeoi = G.GetGeometryData(i + 1);
                        jGeo.Add(jGeoi);
                    }
                    jGear["Geometry"] = jGeo;

                    // 항상 Geometry 계산 후 사용 필요
                    double[] z = new double[4];
                    z[0] = Math.Abs(G.z[1]);
                    z[1] = Math.Abs(G.z[2]);
                    z[2] = Math.Abs(G.z[3]);
                    z[3] = Math.Abs(G.z[4]);

                    jLC = input.mainForm.GetLoadSpectrum_Duty(input.mainForm.DGV_Dutycycle, input.mainForm.DGV_Factors);
                    jLC_result = input.mainForm.CalcPowerFlow(jLC, input.mainForm.Drop_SelectGearType.SelectedIndex, z);
                    calcKV = input.mainForm.CB_CalcKV.Checked;

                    JObject jLC_total = new JObject();
                    jLC_total.Add("Gear", null);
                    jLC_total.Add("Pair", null);
                    jLC_total.Add("Efficiency", null);
                    jLC_total.Add("TotalHr", null);

                    JObject LC = new JObject();
                    LC.Add("Input", jLC);
                    LC.Add("Output", jLC_result);
                    LC.Add("Total", jLC_total);
                    jGear["LC"] = LC;

                    // 4. Geometry 및 Rating (이 부분은 병렬 처리 가능)
                    LoadSpectrum LS = new LoadSpectrum();
                    LS.LoadSpectrum_OnlyRating(jGear, G, calcKV);

                    double SHmin = ExtensionMethods.JTokentoDouble(jGear["LC"]["Total"]["S_Hmin"]);
                    double SFmin = ExtensionMethods.JTokentoDouble(jGear["LC"]["Total"]["S_Fmin"]);

                    double calcSHmin = ExtensionMethods.JTokentoDouble(jGear["LC"]["Total"]["Calculated S_Hmin"]);
                    double calcSFmin = ExtensionMethods.JTokentoDouble(jGear["LC"]["Total"]["Calculated S_Fmin"]);

                    // DataRow 접근도 동기화 (row는 lock으로 이미 보호됨)
                    row["min. S_H"] = Math.Round(calcSHmin, 6);
                    row["min. S_F"] = Math.Round(calcSFmin, 6);
                }
                catch (Exception ex)
                {
                    // Rating 계산 중 오류 발생 시 기본값 설정
                    System.Diagnostics.Debug.WriteLine($"Rating calculation error for z1={z1}, z2={z2}, m_n={m_n}: {ex.Message}");
                    row["min. S_H"] = "Error";
                    row["min. S_F"] = "Error";

                    // 에러 발생 시 계속 진행
                }
            }
            return row; // 처리된 행 반환
        }
        private static SimpleSizingOutput CreateOutput(DataTable allCombinations, DataTable gearCombinations, DataTable moduleCombinations, TimeSpan calctime, SimpleSizingInput input, bool withRating)
        {

            // 5. 결과 sorting
            DataTable filteredResults = allCombinations.Clone();

            var filteredRows = allCombinations.AsEnumerable()
                .Where(row =>
                {
                    try
                    {
                        double a = Convert.ToDouble(row["a [mm]"]);
                        double d1 = Convert.ToDouble(row["d_a1 [mm]"]);
                        double d2 = Convert.ToDouble(row["d_a2 [mm]"]);

                        bool dimensionCheck = a >= input.a_min && a <= input.a_max &&
                                            d1 >= input.d_min && d1 <= input.d_max &&
                                            d2 >= input.d_min && d2 <= input.d_max;

                        if (!dimensionCheck) return false;

                        // Rating 체크 (withRating이 true일 때만)
                        if (withRating)
                        {
                            // 안전한 변환을 위해 null 체크 및 문자열 처리
                            var sHValue = row["min. S_H"];
                            var sFValue = row["min. S_F"];
                            
                            // null이거나 "Error"인 경우 해당 행은 제외
                            if (sHValue == null || sFValue == null || 
                                sHValue.ToString() == "Error" || sFValue.ToString() == "Error" ||
                                string.IsNullOrEmpty(sHValue.ToString()) || string.IsNullOrEmpty(sFValue.ToString()))
                            {
                                return false;
                            }
                            
                            if (!double.TryParse(sHValue.ToString(), out double sH) ||
                                !double.TryParse(sFValue.ToString(), out double sF))
                            {
                                return false;
                            }
                            
                            return sH >= input.min_contact_safety_factor && 
                                   sF >= input.min_bending_safety_factor;
                        }

                        return true;
                    }
                    catch
                    {
                        // 변환 실패 시 해당 행은 제외
                        return false;
                    }
                });

            foreach (var row in filteredRows)
            {
                filteredResults.ImportRow(row);
            }

            // 6. 결과 반환
            SimpleSizingOutput output = new SimpleSizingOutput();

            output.totalcases = gearCombinations.Rows.Count * moduleCombinations.Rows.Count;
            output.calculationcases = allCombinations.Rows.Count;
            output.Filteredcases = filteredResults.Rows.Count;
            output.GearList = allCombinations;
            output.FilteredResults = filteredResults;
            output.CalcTime = calctime.TotalSeconds;

            return output;
        }
    }
}

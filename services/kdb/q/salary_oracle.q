/ Nyx Venatrix - Salary Oracle (kdb+/q)
/ Estimates market salary ranges based on job data

/ Sample salary database (in production, this would be populated from real data)
salaryData:([]
  jobTitle:(`SoftwareEngineer`SeniorEngineer`LeadEngineer`DataScientist`MLEngineer`DevOpsEngineer);
  seniorityLevel:(`Junior`Mid`Senior`Mid`Senior`Mid);
  location:(`"San Francisco"`"San Francisco"`"New York"`"San Francisco"`"Boston"`"Austin");
  minSalary:120000 150000 200000 140000 180000 130000;
  maxSalary:160000 190000 270000 180000 240000 170000;
  medianSalary:140000 170000 235000 160000 210000 150000
 )

/ Function to normalize job title
normalizeTitle:{[title]
  / Simple normalization - in production would use fuzzy matching
  lower:lower title;
  $[lower like "*senior*";`SeniorEngineer;
    lower like "*lead*";`LeadEngineer;
    lower like "*data*";`DataScientist;
    lower like "*ml*";`MLEngineer;
    lower like "*devops*";`DevOpsEngineer;
    `SoftwareEngineer]
 }

/ Function to estimate salary based on job metadata
estimateSalary:{[jobTitle;location;seniority]
  / Normalize inputs
  normTitle:normalizeTitle jobTitle;

  / Query database
  matches:select from salaryData where jobTitle=normTitle;

  / If no exact match, use generic software engineer
  $[0=count matches;
    matches:select from salaryData where jobTitle=`SoftwareEngineer;
    matches];

  / Location adjustments (San Francisco = 1.0x baseline)
  locationMultiplier:$[location like "*San Francisco*";1.0;
                       location like "*New York*";0.95;
                       location like "*Boston*";0.85;
                       location like "*Austin*";0.80;
                       0.75]; / Default for other cities

  / Seniority adjustments
  seniorityMultiplier:$[seniority like "*Senior*";1.15;
                         seniority like "*Lead*";1.30;
                         seniority like "*Staff*";1.45;
                         1.0]; / Default

  / Calculate adjusted ranges
  baseMin:first exec minSalary from matches;
  baseMax:first exec maxSalary from matches;
  baseMedian:first exec medianSalary from matches;

  adjustedMin:`int$baseMin*locationMultiplier*seniorityMultiplier;
  adjustedMax:`int$baseMax*locationMultiplier*seniorityMultiplier;
  adjustedMedian:`int$baseMedian*locationMultiplier*seniorityMultiplier;

  / Return result as dictionary
  `minSalary`maxSalary`medianSalary`currency`confidence!(adjustedMin;adjustedMax;adjustedMedian;`USD;0.75)
 }

/ HTTP API endpoint handler
.z.ph:{[request]
  / Parse query params (simplified - real implementation would use proper HTTP parsing)
  params:.h.uh request;

  / Extract job data
  title:params[`title];
  location:params[`location];
  seniority:params[`seniority];

  / Estimate salary
  result:estimateSalary[title;location;seniority];

  / Return as JSON
  .h.hy[`json] .j.j result
 }

/ Initialize
.z.pi:5000 / Port
-1"Nyx Venatrix Salary Oracle initialized on port 5000";
-1"Sample query: GET http://localhost:5000/?title=Software Engineer&location=San Francisco&seniority=Mid";

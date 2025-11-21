/ Salary Oracle
/ Schema
salaryPoints: flip `ts`title`location`seniority`yoe`industry`company`currency`amount!(
  "p"$();
  "s"$();
  "s"$();
  "s"$();
  "f"$();
  "s"$();
  "s"$();
  "s"$();
  "f"$()
 );

/ Dummy data for testing
`salaryPoints insert (2024.01.01D12:00:00.000; `SoftwareEngineer; `London; `Senior; 5.0; `Tech; `Google; `GBP; 90000.0);
`salaryPoints insert (2024.01.02D12:00:00.000; `SoftwareEngineer; `London; `Senior; 6.0; `Tech; `Meta; `GBP; 95000.0);
`salaryPoints insert (2024.01.03D12:00:00.000; `SoftwareEngineer; `London; `Mid; 3.0; `Tech; `Amazon; `GBP; 65000.0);
`salaryPoints insert (2024.01.04D12:00:00.000; `DataScientist; `NewYork; `Senior; 5.0; `Finance; `JPM; `USD; 150000.0);

/ Function: getSalaryRange
/ Args: title (sym), location (sym), seniority (sym), yoe (float), industry (sym)
getSalaryRange:{[t;l;s;y;i]
  / Filter matches
  data: select amount, currency from salaryPoints
        where title=t, location=l, seniority=s;

  / If not enough data, relax constraints (e.g. ignore seniority)
  if[5 > count data;
    data: select amount, currency from salaryPoints where title=t, location=l
  ];

  / Calculate stats
  res: 0!select low: 0.25 xquantile amount,
                mid: med amount,
                high: 0.75 xquantile amount,
                count: count i
         by currency from data;

  : res
 };

/ Expose on port 5000
\p 5000

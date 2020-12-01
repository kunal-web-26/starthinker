###########################################################################
#
#  Copyright 2020 Google LLC
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
###########################################################################

from starthinker.util.bigquery import query_to_view
from starthinker.util.bigquery import table_create
from starthinker.util.csv import rows_pad
from starthinker.util.data import get_rows
from starthinker.util.data import put_rows
from starthinker.util.google_api import API_DV360
from starthinker.util.google_api.discovery_to_bigquery import Discovery_To_BigQuery
from starthinker.util.project import project
from starthinker.util.regexp import lookup_id
from starthinker.util.sheets import sheets_clear

from starthinker.task.dv_sheets.patch import patch_clear
from starthinker.task.dv_sheets.patch import patch_log
from starthinker.task.dv_sheets.patch import patch_masks
from starthinker.task.dv_sheets.patch import patch_preview


def line_item_clear():
  table_create(
      project.task["auth_bigquery"],
      project.id,
      project.task["dataset"],
      "DV_LineItems",
      Discovery_To_BigQuery("displayvideo",
                            "v1").method_schema("advertisers.lineItems.list"),
  )

  sheets_clear(project.task["auth_sheets"], project.task["sheet"], "Line Items",
               "A2:Z")


def line_item_load():

  # load multiple partners from user defined sheet
  def line_item_load_multiple():
    rows = get_rows(
        project.task["auth_sheets"], {
            "sheets": {
                "sheet": project.task["sheet"],
                "tab": "Advertisers",
                "range": "A2:A"
            }
        })

    for row in rows:
      yield from API_DV360(
          project.task["auth_dv"], iterate=True).advertisers().lineItems().list(
              advertiserId=lookup_id(row[0])).execute()

  # write line_items to database
  put_rows(
      project.task["auth_bigquery"], {
          "bigquery": {
              "dataset":
                  project.task["dataset"],
              "table":
                  "DV_LineItems",
              "schema":
                  Discovery_To_BigQuery(
                      "displayvideo",
                      "v1").method_schema("advertisers.lineItems.list"),
              "format":
                  "JSON"
          }
      }, line_item_load_multiple())

  # write line_items to sheet
  rows = get_rows(
      project.task["auth_bigquery"], {
          "bigquery": {
              "dataset":
                  project.task["dataset"],
              "query":
                  """SELECT
         CONCAT(P.displayName, ' - ', P.partnerId),
         CONCAT(A.displayName, ' - ', A.advertiserId),
         CONCAT(C.displayName, ' - ', C.campaignId),
         CONCAT(I.displayName, ' - ', I.insertionOrderId),
         CONCAT(L.displayName, ' - ', L.lineItemId),
         'PATCH',
         L.entityStatus,
         ARRAY_TO_STRING(L.warningMessages, '\\n'),

         L.flight.flightDateType,
         L.flight.flightDateType,
         CONCAT(L.flight.dateRange.startDate.year, '-', L.flight.dateRange.startDate.month, '-', L.flight.dateRange.startDate.day),
         CONCAT(L.flight.dateRange.startDate.year, '-', L.flight.dateRange.startDate.month, '-', L.flight.dateRange.startDate.day),
         CONCAT(L.flight.dateRange.endDate.year, '-', L.flight.dateRange.endDate.month, '-', L.flight.dateRange.endDate.day),
         CONCAT(L.flight.dateRange.endDate.year, '-', L.flight.dateRange.endDate.month, '-', L.flight.dateRange.endDate.day),
         L.flight.triggerId,
         L.flight.triggerId,

         L.budget.budgetAllocationType,
         L.budget.budgetAllocationType,
         L.budget.budgetUnit,
         L.budget.budgetUnit,
         L.budget.maxAmount / 1000000,
         L.budget.maxAmount / 1000000,

         L.partnerRevenueModel.markupType,
         L.partnerRevenueModel.markupType,
         CAST(L.partnerRevenueModel.markupAmount AS FLOAT64) / 1000000,
         CAST(L.partnerRevenueModel.markupAmount AS FLOAT64) / 1000000,

         CAST(L.conversionCounting.postViewCountPercentageMillis AS Float64) / 1000,
         CAST(L.conversionCounting.postViewCountPercentageMillis AS Float64) / 1000,

         L.targetingExpansion.targetingExpansionLevel,
         L.targetingExpansion.targetingExpansionLevel,
         L.targetingExpansion.excludeFirstPartyAudience,
         L.targetingExpansion.excludeFirstPartyAudience,

         FROM `{dataset}.DV_LineItems` AS L
         LEFT JOIN `{dataset}.DV_Advertisers` AS A
         ON L.advertiserId=A.advertiserId
         LEFT JOIN `{dataset}.DV_Campaigns` AS C
         ON L.advertiserId=C.advertiserId
         LEFT JOIN `{dataset}.DV_InsertionOrders` AS I
         ON L.advertiserId=I.advertiserId
         LEFT JOIN `{dataset}.DV_Partners` AS P
         ON A.partnerId=P.partnerId
       """.format(**project.task),
              "legacy":
                  False
          }
      })

  put_rows(
      project.task["auth_sheets"], {
          "sheets": {
              "sheet": project.task["sheet"],
              "tab": "Line Items",
              "range": "A2"
          }
      }, rows)


def line_item_audit():

  rows = get_rows(
      project.task["auth_sheets"], {
          "sheets": {
              "sheet": project.task["sheet"],
              "tab": "Line Items",
              "range": "A2:Z"
          }
      })

  put_rows(
      project.task["auth_bigquery"], {
          "bigquery": {
              "dataset": project.task["dataset"],
              "table": "SHEET_LineItems",
              "schema": [
                  { "name": "Partner", "type": "STRING" },
                  { "name": "Advertiser", "type": "STRING" },
                  { "name": "Campaign", "type": "STRING" },
                  { "name": "Insertion_Order", "type": "STRING" },
                  { "name": "Line_Item", "type": "STRING" },
                  { "name": "Action", "type": "STRING" },
                  { "name": "Status", "type": "STRING" },
                  { "name": "Warning", "type": "STRING" },
                  { "name": "Flight_Data_Type", "type": "STRING" },
                  { "name": "Flight_Data_Type_Edit", "type": "STRING" },
                  { "name": "Flight_Start_Date", "type": "STRING" },
                  { "name": "Flight_Start_Date_Edit", "type": "STRING" },
                  { "name": "Flight_End_Date", "type": "STRING" },
                  { "name": "Flight_End_Date_Edit", "type": "STRING" },
                  { "name": "Flight_Trigger", "type": "STRING" },
                  { "name": "Flight_Trigger_Edit", "type": "STRING" },
                  { "name": "Budget_Allocation_Type", "type": "STRING" },
                  { "name": "Budget_Allocation_Type_Edit", "type": "STRING" },
                  { "name": "Budget_Unit", "type": "STRING" },
                  { "name": "Budget_Unit_Edit", "type": "STRING" },
                  { "name": "Budget_Max", "type": "FLOAT" },
                  { "name": "Budget_Max_Edit", "type": "FLOAT" },
                  { "name": "Partner_Revenue_Model", "type": "STRING" },
                  { "name": "Partner_Revenue_Model_Edit", "type": "STRING" },
                  { "name": "Partner_Markup", "type": "FLOAT" },
                  { "name": "Partner_Markup_Edit", "type": "FLOAT" },
                  { "name": "Conversion_Percent", "type": "FLOAT" },
                  { "name": "Conversion_Percent_Edit", "type": "FLOAT" },
                  { "name": "Targeting_Expansion_Level", "type": "STRING" },
                  { "name": "Targeting_Expansion_Level_Edit", "type": "STRING" },
                  { "name": "Exclude_1P", "type": "STRING" },
                  { "name": "Exclude_1P_Edit", "type": "STRING" },
              ],
              "format": "CSV"
          }
      }, rows)

  # Create Audit View
  query_to_view(
      project.task["auth_bigquery"],
      project.id,
      project.task["dataset"],
      "AUDIT_LineItems",
      """WITH
      /* Check if sheet values are set */
      INPUT_ERRORS AS (
        SELECT
        *
        FROM (
          SELECT
            'Line Item' AS Operation,
            CASE
              WHEN Budget_Allocation_Type_Edit IS NULL THEN 'Missing Budget Allocation Type.'
              WHEN Budget_Unit_Edit IS NULL THEN 'Missing Budget Unit.'
              WHEN Budget_Max_Edit IS NULL THEN 'Missing Budget Max.'
              WHEN Partner_Revenue_Model_Edit IS NULL THEN 'Missing Partner Revenue Model.'
              WHEN Partner_Markup_Edit IS NULL THEN 'Missing Partner Markup.'
              WHEN Conversion_Percent_Edit IS NULL THEN 'Missing Conversions Percent Edit.'
              WHEN Targeting_Expansion_Level_Edit IS NULL THEN 'Missing Targeting Expansion Level.'
              WHEN Exclude_1P_Edit IS NULL THEN 'Missing Exclude 1P.'
            ELSE
              NULL
            END AS Error,
            'ERROR' AS Severity,
          COALESCE(Line_Item, 'BLANK') AS Id
        FROM
          `{dataset}.SHEET_LineItems`
        )
        WHERE
          Error IS NOT NULL
      )

      SELECT * FROM INPUT_ERRORS
      ;
    """.format(**project.task),
      legacy=False)


def line_item_patch(commit=False):

  def date_edited(value):
    y, m, d = value.split("-")
    return {"year": y, "month": m, "day": d}

  patches = []

  rows = get_rows(
      project.task["auth_sheets"], {
          "sheets": {
              "sheet": project.task["sheet"],
              "tab": "Line Items",
              "range": "A2:AZ"
          }
      })

  rows = rows_pad(rows, 31, "")

  for row in rows:
    if row[4] == "DELETE":
      patches.append({
          "operation": "Line Items",
          "action": "DELETE",
          "partner": row[0],
          "advertiser": row[1],
          "campaign": row[2],
          "line_item": row[4],
          "parameters": {
              "advertiserId": lookup_id(row[1]),
              "lineItemId": lookup_id(row[4])
          }
      })

    elif row[5] == "PATCH":
      line_item = {}

      if row[8] != row[9]:
        line_item.setdefault("flight", {})
        line_item["flight"]["flightDateType"] = row[9]
      if row[10] != row[11]:
        line_item.setdefault("flight", {}).setdefault("dateRange", {})
        line_item["flight"]["dateRange"]["startDate"] = date_edited(row[11])
      if row[12] != row[13]:
        line_item.setdefault("flight", {}).setdefault("endDate", {})
        line_item["flight"]["dateRange"]["endDate"] = date_edited(row[13])
      if row[14] != row[15]:
        line_item.setdefault("flight", {})
        line_item["flight"]["triggerId"] = row[15]
      if row[16] != row[17]:
        line_item.setdefault("budget", {})
        line_item["budget"]["budgetAllocationType"] = row[17]
      if row[18] != row[19]:
        line_item.setdefault("budget", {})
        line_item["budget"]["budgetUnit"] = row[19]
      if row[20] != row[21]:
        line_item.setdefault("budget", {})
        line_item["budget"]["maxAmount"] = int(float(row[21]) * 1000000)
      if row[22] != row[23]:
        line_item.setdefault("partnerRevenueModel", {})
        line_item["partnerRevenueModel"]["markupType"] = row[23]
      if row[24] != row[25]:
        line_item.setdefault("partnerRevenueModel", {})
        line_item["partnerRevenueModel"]["markupAmount"] = int(
            float(row[25]) * 1000000)
      if row[26] != row[27]:
        line_item.setdefault("conversionCounting", {})
        line_item["conversionCounting"]["postViewCountPercentageMillis"] = int(
            float(row[27]) * 1000)
      if row[28] != row[29]:
        line_item.setdefault("targetingExpansion", {})
        line_item["targetingExpansion"]["targetingExpansionLevel"] = row[29]
      if row[30] != row[31]:
        line_item.setdefault("targetingExpansion", {})
        line_item["targetingExpansion"]["excludeFirstPartyAudience"] = row[31]

      if line_item:
        patches.append({
            "operation": "Line Items",
            "action": "PATCH",
            "partner": row[0],
            "advertiser": row[1],
            "campaign": row[2],
            "line_item": row[4],
            "parameters": {
                "advertiserId": lookup_id(row[1]),
                "lineItemId": lookup_id(row[4]),
                "body": line_item
            }
        })

  patch_masks(patches)

  if commit:
    line_item_commit(patches)
  else:
    patch_preview(patches)


def line_item_insert(commit=False):
  inserts = []

  rows = get_rows(
    project.task["auth_bigquery"],
    { "bigquery": {
      "dataset": project.task["dataset"],
      "table":"INSERT_LineItems",
    }},
    as_object=True
  )

  for row in rows:
    inserts.append({
      "operation": "Line Items",
      "action": "INSERT",
      "partner": None,
      "advertiser": row['advertiserId'],
      "campaign": row['campaignId'],
      "line_item": row['displayName'],
      "parameters": {
        "advertiserId": row['advertiserId'],
        "body":row
      }
    })

  if commit:
    line_item_commit(inserts)
  else:
    patch_preview(inserts)


def line_item_commit(patches):
  for patch in patches:
    if not patch.get("line_item"):
      continue
    print("API LINE ITEM:", patch["action"], patch["line_item"])
    try:
      if patch["action"] == "DELETE":
        response = API_DV360(
          project.task["auth_dv"]
        ).advertisers().lineItems().delete(
          **patch["parameters"]
        ).execute()
        patch["success"] = response
      elif patch["action"] == "PATCH":
        response = API_DV360(
          project.task["auth_dv"]
        ).advertisers().lineItems().patch(
          **patch["parameters"]
        ).execute()
        patch["success"] = response["lineItemId"]
      elif patch["action"] == "INSERT":
        response = API_DV360(
          project.task["auth_dv"]
        ).advertisers().lineItems().create(
          **patch["parameters"]
        ).execute()
        patch["success"] = response["lineItemId"]
    except Exception as e:
      patch["error"] = str(e)
    finally:
      patch_log(patch)
  patch_log()
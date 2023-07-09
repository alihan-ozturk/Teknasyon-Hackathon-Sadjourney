import boto3
import datetime
import math
import awswrangler as wr
from k_means_constrained import KMeansConstrained

dynamodb = boto3.client("dynamodb")
days = ["mo", "tu", "we", "th", "fr", "sa", "su"]

max_number_of_passenger = 9
min_number_of_passenger = 5

today = datetime.date.today()
day_number = today.isoweekday() - 1


def lambda_handler(event, context):
    employees = wr.dynamodb.read_partiql_query(
        query=f"""SELECT id, lattitude, longitude FROM Employee WHERE {days[day_number]}=?""",
        parameters=[True])

    drivers = wr.dynamodb.read_partiql_query(
        query=f"""SELECT id FROM Driver WHERE isAvailable=?""",
        parameters=[True]).values

    X = employees.loc[:, ["lattitude", "longitude"]]

    number_of_service = math.ceil(len(employees) / max_number_of_passenger)

    kmeans = KMeansConstrained(
        n_clusters=number_of_service,
        size_min=min_number_of_passenger,
        size_max=max_number_of_passenger,
        random_state=0
    )

    employees["DriverInd"] = kmeans.fit_predict(X.values)

    for i in range(len(employees)):
        dynamodb.update_item(
            TableName="Employee",
            Key={'id': {'S': employees.loc[i, "id"]}},
            UpdateExpression=f"SET driverId = :val",
            ExpressionAttributeValues={':val': {'S': drivers[employees.loc[i, "DriverInd"]][0]}})

    grouped = employees.groupby('DriverInd')['id'].apply(list).reset_index()

    for i in range(len(grouped)):
        dynamodb.update_item(
            TableName="Driver",
            Key={'id': {'S': drivers[i][0]}},
            UpdateExpression=f"SET employeeIds = :val",
            ExpressionAttributeValues={':val': {'S': ",".join(grouped.loc[i, "id"])}})

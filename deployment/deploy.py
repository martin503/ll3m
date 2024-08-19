from prefect import serve

from deployment.configs import Monitor
from deployment.flows import archive, eval, monitor, promote, release, train

if __name__ == "__main__":
    train = train.to_deployment(name="Train")
    eval = eval.to_deployment(name="Eval")
    promote = promote.to_deployment(name="Promote")
    archive = archive.to_deployment(name="Archive")
    release = release.to_deployment(name="Release")
    monitor = monitor.to_deployment(
        name="Monitor Champ", interval=180, parameters={"cfg": Monitor().model_dump()}
    )
    serve(train, eval, promote, archive, release, monitor)

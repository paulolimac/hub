## Textilla on Stencila Hub

Textilla is Texture plus Stencila: it add reproducible elements like code cells, reproducible figures, and spreadsheets to Texture. This sub-folder provides a deployment of Textilla as a microservice within Stencila Hub.

### Run locally

To run locally, in the top-level folder run,

```bash
make textilla-run
```

You can then access the test Dar at http://localhost:4000/edit/textilla


### Run within Docker


```bash
make textilla-rundocker
```

This will mount the `dars` folder into the Docker container so you should be able to access the test Dar via the same URL http://localhost:4000/edit/textilla. Note that this is a test development setup only and due to how the `dars` folder is mounted, and because the container runs as non-root user, that you won't be able to save any changes.


### Run via `router`

The [`router`](../../router) routes requests to Stencila Hub's various microservices. To test that is working run,

```bash
make router-rundocker
make textilla-rundocker
```

Now you should be able to use Textilla at http://localhost:3000/edit/textilla (note the different port number).

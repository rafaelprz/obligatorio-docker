#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <semaphore.h>
#include <time.h>
#include <unistd.h>
#include <stdint.h>

#define MAX_BARRA 8 // Cuantos platos pueden estar en la barra al mismo tiempo
#define MAX_PLATOS 50 // Cuantos platos se cocinarán en total (entre todos los cocineros)
#define TIEMPO_MAX_COCINA 3 // Tiempo máximo que tarda un cocinero en cocinar un plato (en segundos)
#define TIEMPO_MAX_ENTREGA 2 // Tiempo máximo que tarda un mozo en llevar un plato al cliente (en segundos)
#define NUM_COCINEROS 5 // Cantidad de cocineros que cocinarán los platos
#define NUM_MOZOS 10 // Cantidad de mozos que llevarán los platos a los clientes

int barra[MAX_BARRA];
int pos_insert = 0;
int pos_extract = 0;
int cant_en_barra = 0;
int cant_total_platos_cocinados = 0;

sem_t mutex_barra;
sem_t mutex_cant_total_platos_cocinados;
sem_t barra_llena;
sem_t barra_vacia;
// V(x) -> sem_post(x)
// P(x) -> sem_wait(x)

void insertar() {
    barra[pos_insert] = 1;
    pos_insert = (pos_insert + 1) % MAX_BARRA;
    cant_en_barra++;
}

void extraer() {
    barra[pos_extract] = 0;
    pos_extract = (pos_extract + 1) % MAX_BARRA;
    cant_en_barra--;
}

void *cocinero(void *arg)
{
	int numeroCocinero = *(int *)arg;

    while (1)
    {        
        
		int r = rand() % TIEMPO_MAX_COCINA;
		sleep(1+r); // Simula el tiempo de cocinar un plato (hasta 3 segundos)
		
        sem_wait(&mutex_cant_total_platos_cocinados);
        if (cant_total_platos_cocinados >= MAX_PLATOS) { 
            sem_post(&mutex_cant_total_platos_cocinados);
            break; // Si ya se cocinaron 50 platos se detiene
        }
        cant_total_platos_cocinados++;
        sem_post(&mutex_cant_total_platos_cocinados);

		printf("Cocinero %d preparó un plato \n", numeroCocinero);

        sem_wait(&barra_llena); // Espera a que haya espacio en la barra
        sem_wait(&mutex_barra);

        insertar();
		printf("Cocinero %d dejó un plato en la barra (platos en barra: %d) \n", numeroCocinero, cant_en_barra);

        sem_post(&mutex_barra);
        sem_post(&barra_vacia); // Indica que la barra tiene un plato más
    }

    return NULL;
}

void *mozo(void *arg)
{
    int numeroMozo = *(int *)arg;

    while (1)
    {   
        sem_wait(&barra_vacia); // Espera si no hay platos en la barra
        sem_wait(&mutex_barra);
    
		sem_wait(&mutex_cant_total_platos_cocinados);
        if (cant_total_platos_cocinados >= MAX_PLATOS && cant_en_barra == 0) {
            sem_post(&mutex_barra); 
			sem_post(&mutex_cant_total_platos_cocinados);
            break; // Si los cocineron ya terminaron y no hay mas platos para entregar se detiene
        }
        sem_post(&mutex_cant_total_platos_cocinados);

        extraer();
        printf("Mozo %d retiró un plato de la barra (platos en barra: %d) \n", numeroMozo, cant_en_barra);

        
        sem_post(&mutex_barra);
        sem_post(&barra_llena); // Indica que la barra tiene un plato menos

		int r = rand() % TIEMPO_MAX_ENTREGA;
		sleep(1+r); // Simula el tiempo de entregar un plato (hasta 2 segundos)
        printf("Mozo %d entregó un plato \n", numeroMozo);
    
    }
	return NULL;
}


int main()
{
	pthread_t cocinero1, cocinero2, cocinero3, cocinero4, cocinero5;
    pthread_t mozo1, mozo2, mozo3, mozo4, mozo5, mozo6, mozo7, mozo8, mozo9, mozo10;
    pthread_attr_t attr;
    pthread_attr_init(&attr);

	// Inicialización de semáforos
	sem_init(&mutex_barra, 0, 1);
    sem_init(&mutex_cant_total_platos_cocinados, 0, 1);
	sem_init(&barra_llena, 0, MAX_BARRA); // "Cantidad de espacios libres en la barra" - Obliga a esperar si la barra está llena
	sem_init(&barra_vacia, 0, 0); // "Cantidad de espacios ocupados en la barra" - Obliga a esperar si la barra está vacía

	// Cobegin cocineros
	int ids_cocineros[NUM_COCINEROS];
	for (int i = 0; i < NUM_COCINEROS; i++) {
		ids_cocineros[i] = i + 1; // IDs de cocineros del 1 al 5
	}
	pthread_create(&cocinero1, &attr, cocinero, &ids_cocineros[0]);
    pthread_create(&cocinero2, &attr, cocinero, &ids_cocineros[1]);
    pthread_create(&cocinero3, &attr, cocinero, &ids_cocineros[2]);
    pthread_create(&cocinero4, &attr, cocinero, &ids_cocineros[3]);
    pthread_create(&cocinero5, &attr, cocinero, &ids_cocineros[4]);

    // Cobegin mozos
	int ids_mozos[NUM_MOZOS];
	for (int i = 0; i < NUM_MOZOS; i++) {
		ids_mozos[i] = i + 1; // IDs de mozos del 1 al 10
	}
	pthread_create(&mozo1, &attr, mozo, &ids_mozos[0]);
    pthread_create(&mozo2, &attr, mozo, &ids_mozos[1]);
    pthread_create(&mozo3, &attr, mozo, &ids_mozos[2]);
    pthread_create(&mozo4, &attr, mozo, &ids_mozos[3]);
    pthread_create(&mozo5, &attr, mozo, &ids_mozos[4]);
    pthread_create(&mozo6, &attr, mozo, &ids_mozos[5]);
    pthread_create(&mozo7, &attr, mozo, &ids_mozos[6]);
    pthread_create(&mozo8, &attr, mozo, &ids_mozos[7]);
    pthread_create(&mozo9, &attr, mozo, &ids_mozos[8]);
    pthread_create(&mozo10, &attr, mozo, &ids_mozos[9]);


	// Coend cocineros
    pthread_join(cocinero1, NULL);
    pthread_join(cocinero2, NULL);
    pthread_join(cocinero3, NULL);
    pthread_join(cocinero4, NULL);
    pthread_join(cocinero5, NULL);

	for (int i = 0; i < NUM_MOZOS; i++) {
        sem_post(&barra_vacia); // Despierta a los mozos que puedan estar esperando por platos en la barra
    }

    // Coend mozos
    pthread_join(mozo1, NULL);
    pthread_join(mozo2, NULL);
    pthread_join(mozo3, NULL);
    pthread_join(mozo4, NULL);
    pthread_join(mozo5, NULL);
    pthread_join(mozo6, NULL);
    pthread_join(mozo7, NULL);
    pthread_join(mozo8, NULL);
    pthread_join(mozo9, NULL);
    pthread_join(mozo10, NULL);

    printf("Se cocinaron y entregaron un total de %d platos. La ejecución termina. \n", cant_total_platos_cocinados);

	return 0;
}